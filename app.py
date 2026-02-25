import streamlit as st
import base64
from agent import (
    analyze_and_generate, 
    get_db, 
    generate_review_plan, 
    generate_special_topic
)

# 页面基础配置
st.set_page_config(page_title="五年级全科错题辅导小助手", page_icon="👨‍🏫", layout="wide")

# 全局变量定义
SUBJECTS = ["数学", "语文", "英语"]

# 侧边栏导航
st.sidebar.title("🧭 导航菜单")
menu = st.sidebar.radio("请选择功能：", ["📝 错题录入分析", "📚 我的错题本", "🧠 智能复习室（薄弱点攻克）"])

if menu == "📝 错题录入分析":
    st.title("📝 错题录入与分析")
    st.markdown("将平时的错题一键拍照上传，AI 老师帮你诊断解析，并生成专属同类题巩固。记录会被自动保存至“我的错题本”。")
    
    # 录入科目选择
    selected_subject = st.radio("首先，请选择这道错题对应的科目：", SUBJECTS, horizontal=True)
    
    # 提供两种图片录入方式：直接拍照（适合移动端）或 上传图片（适合PC端相册）
    input_method = st.radio("选择错题录入方式：", ["上传图片", "直接拍照"], horizontal=True)
    
    uploaded_file = None
    if input_method == "上传图片":
        uploaded_file = st.file_uploader(f"📸 从相册上传【{selected_subject}】错题图片", type=["png", "jpg", "jpeg"])
    else:
        uploaded_file = st.camera_input(f"📷 手机直接拍摄【{selected_subject}】错题")
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption=f"你提供的{selected_subject}错题图片", use_container_width=True)
        
        if st.button("✨ 开始智能解析", type="primary", use_container_width=True):
            with st.spinner(f"【{selected_subject}】老师正在拿着放大镜分析你的错题，请稍等片刻..."):
                try:
                    # 调用带有科目参数的方法，并生成记录
                    record = analyze_and_generate(uploaded_file, selected_subject)
                    
                    st.success("✅ 解析完成，该记录已自动保存入库！")
                    st.divider()
                    
                    # 展示本次错题诊断报告
                    st.subheader(f"💡 老师的诊断报告（共找到 {len(record.analysis_set.errors)} 道错题）")
                    
                    for i, error_item in enumerate(record.analysis_set.errors, start=1):
                        with st.container():
                            st.markdown(f"#### 🔎 错题 {i}：*{error_item.original_question_text}*")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.info(f"**📉 错误类型：** {error_item.error_type}")
                            with col2:
                                kps = "、".join(error_item.knowledge_points)
                                st.info(f"**📚 核心知识点：** {kps}")
                            
                            st.success(f"**📝 分步解析思路：**\n\n{error_item.step_by_step_explanation}")
                            st.caption(f"💌 **老师悄悄话：** {error_item.encouragement}")
                            st.markdown("---")
                    
                    # 展示本次举一反三题目
                    st.subheader("🎯 护航特训：举一反三(综合能力测试)")
                    for idx, q in enumerate(record.practices.questions, start=1):
                        st.markdown(f"#### 第 {idx} 题 （难度：`{q.difficulty}`）")
                        st.write(q.question_text)
                        with st.expander(f"👀 查看第 {idx} 题的答案与解析"):
                            st.markdown(f"**✅ 答案：** {q.correct_answer}")
                            st.markdown(f"**📖 思路：** {q.explanation}")
                            
                except Exception as e:
                    st.error(f"抱歉，分析过程中遇到问题：{str(e)}")

elif menu == "📚 我的错题本":
    st.title("📚 我的错题本图集")
    st.markdown("这里集中整理了你过去记录的所有错题，方便按科目随时回顾复习。")
    
    records = get_db()
    
    if not records:
        st.warning("📭 目前错题本还是空空如也，先去“错题录入分析”记录几道错题吧！")
    else:
        # 按照科目进行过滤预览
        filter_subject = st.selectbox("筛选要查看的科目", ["全部科目"] + SUBJECTS)
        
        filtered_records = []
        for r in records:
            if filter_subject == "全部科目" or r.subject == filter_subject:
                filtered_records.append(r)
                
        if not filtered_records:
             st.info(f"暂无【{filter_subject}】的错题记录。")
        else:
            st.write(f"共为您找到 **{len(filtered_records)}** 条记录。")
            
            # 以时间倒序输出历史记录（最新的在上面）
            for r in reversed(filtered_records):
                # 提取此记录涵盖的所有知识点
                all_kps = []
                for e in r.analysis_set.errors:
                    all_kps.extend(e.knowledge_points)
                all_kps_str = "、".join(list(set(all_kps)))
                
                with st.expander(f"[{r.subject}] 记录时间：{r.timestamp} | 包含 {len(r.analysis_set.errors)} 题 | 知识点：{all_kps_str}"):
                    img_data = base64.b64decode(r.image_base64)
                    st.image(img_data, caption="原图存档", width=400)
                    st.markdown("---")
                    
                    for i, error_item in enumerate(r.analysis_set.errors, start=1):
                        st.markdown(f"**📌 错题 {i}：** {error_item.original_question_text}")
                        st.markdown(f"- **错误原因：** {error_item.error_type}")
                        st.markdown(f"- **详细解答：** {error_item.step_by_step_explanation}")
                        st.markdown("---")


elif menu == "🧠 智能复习室（薄弱点攻克）":
    st.title("🧠 专属智能复习室")
    st.markdown("我会综合分析你错题本中的高频错误和薄弱点，为你生成科学的复习计划和专属加强包。")
    
    # 只能单科分析比较有针对性
    target_subject = st.selectbox("选择需要生成复习计划的科目", SUBJECTS)
    records = get_db()
    subject_records = [r for r in records if r.subject == target_subject]
    
    if len(subject_records) == 0:
        st.warning(f"目前没有【{target_subject}】的错题记录，无法生成复习计划。多上传几张错题再来吧！")
    else:
        st.info(f"已收集到针对【{target_subject}】的 **{len(subject_records)}** 条错题记录。可以发起复习计划分析了。")
        
        if st.button("🚀 生成全面复习计划＆薄弱点诊断", type="primary"):
            with st.spinner("学霸养成中！教研专家正在深度剖析你的易错知识网..."):
                try:
                    plan = generate_review_plan(subject_records, target_subject)
                    
                    st.divider()
                    st.subheader("📊 核心薄弱环节暴露")
                    
                    # 用于生成后续专项练习的参数串
                    weak_points_list = []
                    
                    for wp in plan.weak_points:
                        weak_points_list.append(wp.knowledge_point)
                        st.error(f"🚨 **预警：{wp.knowledge_point}**  (出错指数：{wp.error_count})")
                        st.markdown(f"> *症结分析：* {wp.analysis}")
                        
                    st.subheader("💡 专家提分建议")
                    st.success(plan.study_advice)
                    
                    st.subheader("📅 拟定复习节奏与计划")
                    st.info(plan.schedule)
                    
                    # 根据提取出来的错题生成专题练习包
                    target_weak_points_str = "、".join(weak_points_list)
                    st.session_state["weak_points"] = target_weak_points_str
                    st.session_state["ready_for_special"] = True
                    
                except Exception as e:
                    st.error(f"分析出错：{str(e)}")
                    
        # 利用 Streamlit 缓存状态控制专项练习生成按钮的出现
        if st.session_state.get("ready_for_special"):
            st.divider()
            st.subheader("🔥 终极冲刺：针对薄弱点生成的专项练习包")
            if st.button("👉 点击生成对应的【专项突击题】（5道）"):
                with st.spinner("出题专家正在疯狂命题中，这些题目将完全针对你的痛点..."):
                    try:
                        special_practice = generate_special_topic(st.session_state["weak_points"], target_subject)
                        for idx, q in enumerate(special_practice.questions, start=1):
                            st.markdown(f"#### 专项第 {idx} 题 （难度：`{q.difficulty}`）")
                            st.write(q.question_text)
                            with st.expander("查看解析与答案"):
                                st.markdown(f"**✅ 答案：** {q.correct_answer}")
                                st.markdown(f"**📖 思路：** {q.explanation}")
                    except Exception as e:
                        st.error(f"生成出错了：{str(e)}")
