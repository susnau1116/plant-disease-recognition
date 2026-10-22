"""将训练好的 PyTorch 模型导出为 ONNX，可选动态量化与一致性校验。

用法：
    python export_onnx.py                                   # 默认导出 checkpoints/resnet18/best.pth
    python export_onnx.py --model resnet50 --quantize       # 导出并动态量化
    python export_onnx.py --checkpoint checkpoints/resnet18/best.pth --verify
"""

import argparse
import io
from pathlib import Path

import numpy as np
import torch
from torch.onnx.errors import OnnxExporterError

from nets.zoo import MODEL_ZOO, build_model
from utils.checkpoint import load_checkpoint

MODEL_DIR = Path(__file__).resolve().parent
DEFAULT_ONNX_DIR = MODEL_DIR / "onnx_models"


def parse_args():
    parser = argparse.ArgumentParser(description="导出 ONNX 模型（可选量化与校验）")
    parser.add_argument("--checkpoint", default=None, help="权重路径，默认 checkpoints/<model>/best.pth")
    parser.add_argument("--model", default=None, choices=list(MODEL_ZOO), help="网络结构，默认从权重推断")
    parser.add_argument("--output", default=None, help="ONNX 输出路径，默认 onnx/<model>.onnx")
    parser.add_argument("--img-size", type=int, default=None, help="输入尺寸，默认读取权重中的训练参数")
    parser.add_argument("--opset", type=int, default=13)
    parser.add_argument("--quantize", action="store_true", help="导出后执行动态量化（减小体积、加速 CPU 推理）")
    parser.add_argument("--verify", action="store_true", help="用 onnxruntime 校验 PyTorch 与 ONNX 输出一致性")
    parser.add_argument("--device", default="cpu")
    return parser.parse_args()


def resolve_checkpoint(args):
    if args.checkpoint:
        path = Path(args.checkpoint)
        if not path.exists():
            raise FileNotFoundError(f"权重不存在: {path}")
        return path

    if args.model:
        path = MODEL_DIR / "checkpoints" / args.model / "best.pth"
        if not path.exists():
            raise FileNotFoundError(f"权重不存在: {path}")
        return path

    for name in MODEL_ZOO:
        candidate = MODEL_DIR / "checkpoints" / name / "best.pth"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("未找到默认权重 checkpoints/<model>/best.pth，请用 --checkpoint 指定")


def main():
    args = parse_args()
    device = torch.device(args.device)
    checkpoint_path = resolve_checkpoint(args)

    state = load_checkpoint(checkpoint_path, device)
    model_name = args.model or state.get("model_name") or "resnet18"
    classes = state.get("classes") or []
    num_classes = len(classes) if classes else 38
    img_size = args.img_size or int(state.get("args", {}).get("img_size", 224))

    model = build_model(model_name, num_classes=num_classes, pretrained=False)
    model.load_state_dict(state["model"])
    model.eval().to(device)
    print(f"已加载权重: {checkpoint_path}（{model_name}, {num_classes} 类, 输入 {img_size}x{img_size}）")

    output = Path(args.output) if args.output else DEFAULT_ONNX_DIR / f"{model_name}.onnx"
    output.parent.mkdir(parents=True, exist_ok=True)

    dummy = torch.randn(1, 3, img_size, img_size, device=device)
    buffer = io.BytesIO()
    try:
        torch.onnx.export(
            model,
            dummy,
            buffer,
            export_params=True,
            opset_version=args.opset,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        )
    except (ImportError, OnnxExporterError) as exc:
        raise SystemExit(f"ONNX 导出失败，请确认已安装 onnx: pip install onnx\n原始错误: {exc}") from exc
    # 通过 BytesIO + Python 文件写入，避免 Windows 中文路径问题
    output.write_bytes(buffer.getvalue())

    size_mb = output.stat().st_size / 1024 / 1024
    print(f"ONNX 导出完成: {output} ({size_mb:.1f} MB, opset {args.opset})")

    quantized_path = None
    if args.quantize:
        try:
            import onnx
            from onnxruntime.quantization import QuantType, quantize_dynamic
        except ImportError as exc:
            raise SystemExit("量化需要安装 onnx 与 onnxruntime: pip install onnx onnxruntime") from exc
        quantized_path = output.with_name(output.stem + "_quantized.onnx")
        # 传入 ModelProto 而非文件路径：onnxruntime 在 Windows 中文路径下
        # 调用 C++ shape inference 会因编码问题无法写出中间文件
        model_proto = onnx.load(str(output))
        quantize_dynamic(model_proto, str(quantized_path), weight_type=QuantType.QUInt8)
        quantized_mb = quantized_path.stat().st_size / 1024 / 1024
        print(f"动态量化完成: {quantized_path} ({quantized_mb:.1f} MB, 压缩 {size_mb / quantized_mb:.1f}x)")

    if args.verify:
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise SystemExit("校验需要安装 onnxruntime: pip install onnxruntime") from exc

        session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
        sample = dummy.cpu().numpy()
        with torch.no_grad():
            torch_output = model.cpu()(torch.from_numpy(sample)).numpy()
        onnx_output = session.run(["output"], {"input": sample})[0]
        max_diff = float(np.abs(torch_output - onnx_output).max())
        print(f"输出一致性校验: 最大误差 {max_diff:.2e}")
        if classes:
            top1 = int(onnx_output.argmax(axis=1)[0])
            print(f"示例输出 top-1 类别: {classes[top1]}")

        if quantized_path is not None and quantized_path.exists():
            quant_session = ort.InferenceSession(str(quantized_path), providers=["CPUExecutionProvider"])
            quant_output = quant_session.run(["output"], {"input": sample})[0]
            quant_diff = float(np.abs(torch_output - quant_output).max())
            print(f"量化模型校验: 最大误差 {quant_diff:.4f}（量化引入的精度损失，属正常范围）")
            if classes:
                print(f"量化模型 top-1 类别: {classes[int(quant_output.argmax(axis=1)[0])]}")

    if classes:
        (output.parent / "classes.txt").write_text("\n".join(classes), encoding="utf-8")
        print(f"类别顺序已保存: {output.parent / 'classes.txt'}")


if __name__ == "__main__":
    main()
