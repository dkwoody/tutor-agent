from pydantic import BaseModel, Field
from typing import List

class Question(BaseModel):
    """单道练习题目的数据结构"""
    difficulty: str = Field(..., description="题目难度，例如：简单、中等、困难")
    question_text: str = Field(..., description="具体的题目内容文本")
    correct_answer: str = Field(..., description="这道练习题的正确答案")
    explanation: str = Field(..., description="详细的解题思路和步骤说明")

class PracticeSet(BaseModel):
    """基于错题衍生生成的练习题集合"""
    questions: List[Question] = Field(..., description="包含错题衍生或专项练习的题目列表")

class ErrorAnalysis(BaseModel):
    """单道错题诊断结果"""
    original_question_text: str = Field(..., description="这道错题的题干内容提取")
    error_type: str = Field(..., description="错误归类，例如：计算错误、审题失误、单词拼写等")
    knowledge_points: List[str] = Field(..., description="这道错题涉及的核心知识点列表")
    step_by_step_explanation: str = Field(..., description="针对这道错题的详细分步解题思路与解析")
    encouragement: str = Field(..., description="给五年级小朋友的一句幽默、温暖的鼓励寄语")

class MultiErrorAnalysis(BaseModel):
    """学生上传的一张图片中可能包含的多道错题诊断结果集合"""
    errors: List[ErrorAnalysis] = Field(..., description="图片中识别出的所有错题的解析列表")

class ErrorRecord(BaseModel):
    """持久化保存的单次错题记录（可能包含该次上传图片中分析出的多题）"""
    id: str = Field(..., description="记录的唯一标识符")
    timestamp: str = Field(..., description="上传或分析的时间戳")
    subject: str = Field(..., description="科目分类，如：语文、数学、英语")
    image_base64: str = Field(..., description="错题原图的 Base64 编码，用于历史回溯")
    analysis_set: MultiErrorAnalysis = Field(..., description="该图片中所有错题的 AI 诊断分析结果集合")
    practices: PracticeSet = Field(..., description="针对这批错题综合生成的举一反三衍生题")

class WeakPoint(BaseModel):
    """分析出的学生薄弱知识点"""
    knowledge_point: str = Field(..., description="知识点名称")
    error_count: int = Field(..., description="错题关联次数（用于评估薄弱程度）")
    analysis: str = Field(..., description="针对该痛点原因的深度分析")

class ReviewPlan(BaseModel):
    """综合复习计划报告"""
    weak_points: List[WeakPoint] = Field(..., description="知识薄弱点列表")
    study_advice: str = Field(..., description="关于该科目的综合提分建议")
    schedule: str = Field(..., description="具体的复习时间安排或节奏建议")
