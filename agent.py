import base64
import json
import os
import uuid
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from models import ErrorAnalysis, MultiErrorAnalysis, PracticeSet, ErrorRecord, ReviewPlan
from typing import List

# 加载 .env 环境变量
load_dotenv()

# 初始化全局客户端
client = OpenAI()

# 存储历史记录的本地 JSON 文件路径
HISTORY_FILE = "history.json"

def get_db() -> List[ErrorRecord]:
    """读取本地 JSON 持久化的所有历史记录"""
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return [ErrorRecord.model_validate(item) for item in data]
        except Exception:
            return []

def save_record(record: ErrorRecord):
    """保存单条错题记录到本地 JSON"""
    records = get_db()
    records.append(record)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in records], f, ensure_ascii=False, indent=2)

def encode_image(uploaded_file) -> str:
    """辅助函数：将上传的图片转换为 Base64 字符串"""
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode("utf-8")

def analyze_and_generate(uploaded_file, subject: str) -> ErrorRecord:
    """
    核心业务逻辑一：输入图片和科目进行错题解析，并持久化保存历史。
    """
    base64_image = encode_image(uploaded_file)
    
    # --- 阶段一：错题解析 ---
    sys_prompt_analysis = f"""
    你是一位幽默、有耐心的五年级【{subject}】老师。
    请仔细查看学生发来的错题图片，图片中可能包含【多道】不同的错题！
    请你逐一找出图片里面的每一道错题，分别分析它们错在哪里，给出详细解答。
    
    你必须强制返回 JSON 格式，并且所有的说明和解答务必使用【简体中文】，且符合以下 Schema：
    {{
        "errors": [
            {{
                "original_question_text": "提炼原题干内容，如果没有原题可以描述题型",
                "error_type": "string 类型，比如：粗心大意、进位错误、语法错误等",
                "knowledge_points": ["string", "string"],
                "step_by_step_explanation": "string 类型，耐心详尽的分布解题说明",
                "encouragement": "string 类型，给孩子们针对这道题的专属打气"
            }}
        ]
    }}
    （备注：如果有多个错题，请在 errors 列表中给出多个对象；如果只有一道，也必须放在列表中。）
    """
    
    try:
        response_analysis = client.chat.completions.create(
            model="qwen-vl-max",
            messages=[
                {"role": "system", "content": sys_prompt_analysis},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "老师，请帮我看看图片里的这些错题，哪怕有多道题，也要帮我逐一分析。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        analysis_content = response_analysis.choices[0].message.content
        multi_error_analysis = MultiErrorAnalysis.model_validate_json(analysis_content)
    except Exception as e:
        raise RuntimeError(f"解析错题图片时发生异常: {str(e)}")

    # --- 阶段二：举一反三生成衍生题 ---
    all_kps = []
    for error_item in multi_error_analysis.errors:
        all_kps.extend(error_item.knowledge_points)
    
    # 去重知识点
    unique_kps = list(set(all_kps))
    knowledge_str = "、".join(unique_kps)
    
    sys_prompt_practice = f"""
    你现在是一位资深的五年级【{subject}】出题专家。
    刚才老师已经诊断出学生在这批错题中涉及的综合核心知识点是：【{knowledge_str}】。
    请基于这些知识点，为一名五年级的学生出 3 道难度逐渐递进的练习题，用于巩固和举一反三。
    
    你必须强制返回 JSON 格式，并且所有的题目内容和解析务必使用【简体中文】，且符合以下 Schema：
    {{
        "questions": [
            {{
                "difficulty": "简单/中等/困难",
                "question_text": "具体的题目描述，确保适合五年级学生",
                "correct_answer": "正确的结果/答案",
                "explanation": "对应的解题思路和解释"
            }}
        ]
    }}
    """
    
    try:
        response_practice = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": sys_prompt_practice},
                {"role": "user", "content": "请针对这些知识点，给我出 3 道好玩的衍生题吧！"}
            ],
            response_format={"type": "json_object"}
        )
        practice_content = response_practice.choices[0].message.content
        practice_set = PracticeSet.model_validate_json(practice_content)
    except Exception as e:
        raise RuntimeError(f"生成衍生练习题时发生异常: {str(e)}")

    # 封装完整记录并保存到本地
    record = ErrorRecord(
        id=str(uuid.uuid4()),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        subject=subject,
        image_base64=base64_image,
        analysis_set=multi_error_analysis,
        practices=practice_set
    )
    save_record(record)
    
    return record


def generate_review_plan(records: List[ErrorRecord], subject: str) -> ReviewPlan:
    """
    核心业务逻辑二：根据选定科目的历史记录制定复习计划及分析薄弱点。
    """
    # 汇总该科目所有的错题知识点作为分析依据
    kps = []
    for r in records:
        for error_item in r.analysis_set.errors:
            kps.extend(error_item.knowledge_points)
    
    if not kps:
        raise ValueError(f"该科目（{subject}）目前没有任何错题记录，无法生成复习计划。")
        
    kps_str = "、".join(kps)
    sys_prompt = f"""
    你是一位资深的五年级【{subject}】教研专家。请分析这位学生在近期学习中积累的错题知识点记录，提取出其真正薄弱的地方，并制定复习计划。
    
    学生的历史错题覆盖知识点（包含重复项）：【{kps_str}】
    
    你必须强制返回 JSON 格式，并且使用【简体中文】，符合以下 Schema：
    {{
        "weak_points": [
            {{
                "knowledge_point": "提炼出的薄弱知识点名称",
                "error_count": 该知识点在记录中大致对应的错误频次评估（整数类型）,
                "analysis": "核心症结的深入分析，为什么学生容易在这里出错"
            }}
        ],
        "study_advice": "针对改科目的整体学习和提分建议",
        "schedule": "针对性的复习时间表或节奏安排建议"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"请帮我针对近期的{subject}错题，制定一份专属于我的复习计划。"}
            ],
            response_format={"type": "json_object"}
        )
        plan_content = response.choices[0].message.content
        return ReviewPlan.model_validate_json(plan_content)
    except Exception as e:
        raise RuntimeError(f"生成复习计划及薄弱点预测时发生异常: {str(e)}")


def generate_special_topic(weak_points_str: str, subject: str) -> PracticeSet:
    """
    核心业务逻辑三：根据分析得出的核心薄弱点，针对性生成专题巩固练习。
    """
    sys_prompt = f"""
    你是一位资深的五年级【{subject}】出题专家。学生近期的核心薄弱点经过系统诊断为：【{weak_points_str}】。
    请基于这些核心薄弱环节，专门为他量身定制 5 道专项突破训练题。
    
    你必须强制返回 JSON 格式，并且使用【简体中文】，符合以下 Schema：
    {{
        "questions": [
            {{
                "difficulty": "中等/困难/挑战",
                "question_text": "具体的题目描述，确保适合五年级学生并且具有提升效果",
                "correct_answer": "正确的结果/答案",
                "explanation": "对应的详尽解题思路和易错点提醒"
            }}
        ]
    }}
    """
    
    try:
        res = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": "帮我出 5 道针对这些薄弱点的终极专项训练题！"}
            ],
            response_format={"type": "json_object"}
        )
        return PracticeSet.model_validate_json(res.choices[0].message.content)
    except Exception as e:
        raise RuntimeError(f"生成专项训练题时发生异常: {str(e)}")
