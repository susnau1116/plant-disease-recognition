"""API 请求/响应数据模型（Pydantic）。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class Treatment(BaseModel):
    type: str = Field(description="防治类型：农药防治 / 物理防治 / 农业防治")
    name: str
    formulation: Optional[str] = None
    dosage: Optional[str] = None
    usage: Optional[str] = None
    precautions: Optional[str] = None
    expected_effect: Optional[str] = None
    effect_time: Optional[str] = None
    judgement: Optional[str] = None
    fallback: Optional[str] = None


class DiseaseBrief(BaseModel):
    class_name: str
    crop: str
    crop_en: Optional[str] = None
    name_cn: str
    name_en: Optional[str] = None
    healthy: bool
    symptoms: Optional[str] = None


class DiseaseDetail(DiseaseBrief):
    occurrence: Optional[str] = None
    transmission: Optional[str] = None
    treatments: List[Treatment] = []
    examples: List[str] = Field(default=[], description="典型例图 URL（每个类别 2~3 张）")


class TopKItem(BaseModel):
    class_name: str
    name_cn: str
    crop: str
    confidence: float


class PredictResponse(BaseModel):
    class_name: str
    name_cn: str
    crop: str
    healthy: bool
    confidence: float
    top_k: List[TopKItem]
    disease: DiseaseDetail
    inference_ms: float


class CropItem(BaseModel):
    crop: str
    crop_en: Optional[str] = None
    total: int
    healthy: int
    diseased: int


class DiseaseListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DiseaseBrief]


class FaqItem(BaseModel):
    id: int
    category: str
    question: str
    answer: str
    keywords: List[str] = []


class FaqListResponse(BaseModel):
    categories: List[str]
    total: int
    items: List[FaqItem]


class ConsultRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500, description="用户问题")


class ConsultResponse(BaseModel):
    matched: bool
    score: float
    answer: Optional[FaqItem] = None
    related: List[FaqItem] = []
    suggestion: str


class MessageCreate(BaseModel):
    question: str = Field(min_length=1, max_length=500, description="用户问题")
    contact: Optional[str] = Field(default=None, max_length=100, description="联系方式（选填）")


class MessageReply(BaseModel):
    reply: str = Field(min_length=1, max_length=1000, description="回复内容")


class MessageItem(BaseModel):
    id: int
    question: str
    contact: Optional[str] = None
    status: str = Field(description="pending 待回复 / replied 已回复")
    reply: Optional[str] = None
    created_at: str
    replied_at: Optional[str] = None


class MessageListResponse(BaseModel):
    total: int
    items: List[MessageItem]


class HealthResponse(BaseModel):
    status: str
    model: str
    classes: int
    diseases: int
    faqs: int
    version: str
