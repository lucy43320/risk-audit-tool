import streamlit as st
import pandas as pd
from io import BytesIO
import requests
import plotly.express as px

# ===================== 初始化会话变量（必须放最前面） =====================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_doubt_text" not in st.session_state:
    st.session_state.current_doubt_text = ""
if "doubt_df" not in st.session_state:
    st.session_state.doubt_df = None
if "merge_df" not in st.session_state:
    st.session_state.merge_df = None
if "pending_question" not in st.session_state:
    st.session_state.pending_question = ""

# 快捷提问回调函数
def set_q1():
    st.session_state.pending_question = "帮我写一段业务部门核查通知"
def set_q2():
    st.session_state.pending_question = "这个风险怎么写进风控底稿"
def set_q3():
    st.session_state.pending_question = "审计一般会怎么取证核查"
def set_q4():
    st.session_state.pending_question = "这个差异是否会影响增值税申报"

# ===================== 侧边栏：API配置区 =====================
with st.sidebar:
    st.header("⚙️ 系统设置")
    st.markdown("#### DeepSeek AI密钥（选填）")
    api_key = st.text_input("API Key", type="password", placeholder="不填则关闭AI功能", key="apikey_input")
    enable_ai = False
    if api_key.strip() != "":
        enable_ai = True
    st.divider()
    st.caption("密钥仅本地使用，不会上传第三方")

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

def ai_analysis(text, key):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    prompt = """
你是财务风控专员，解读下面账证对账疑点。输出内容结构：
1. 差异原因推测
2. 财务风险提示
3. 核查建议
控制总字数200字以内，语言适合风控审计工作底稿。
对账疑点数据：
""" + text
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    try:
        res = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            return res.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ API返回错误：{res.text}"
    except Exception as e:
        return f"❌ 网络/请求异常：{str(e)}"

def ai_chat(question, base_data, history, key):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    system_prompt = f"""
你是财务风控、信用管理专家。下面是本次对账产生的疑点原始数据，用户所有提问都基于这份数据回答：
【对账疑点数据】
{base_data}
要求：回答贴合企业风控、审计、信用管理场景，专业简洁，适合实习底稿、和业务沟通。
"""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.4
    }
    try:
        res = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            reply = res.json()["choices"][0]["message"]["content"]
            return reply
        else:
            return f"❌ API返回错误：{res.text}"
    except Exception as e:
        return f"❌ 网络/请求异常：{str(e)}"


# ===================== 页面主体 =====================
st.set_page_config(page_title="业财对账与资金内控平台", layout="wide")
st.title("📊 业财对账与资金内控分析平台")
st.markdown("""
> 通用财务对账工具｜账证核对、银行余额调节、应收账龄风控；AI自动疑点解读 + 内置风控问答
""")

tab1, tab2, tab3 = st.tabs([
    "📑 通用双表对账（账证核对+AI问答）",
    "🏦 银行流水对账 & 余额调节表",
    "❤️ 应收台账 | 账龄&信用风险监控"
])

# ===================== Tab1 通用双表对账 + AI对话面板 =====================
with tab1:
    st.subheader("双表勾稽对账，自定义字段映射")
    f1 = st.file_uploader("上传表1（业务表/出库单）", type=["xlsx", "xls"])
    f2 = st.file_uploader("上传表2（凭证表）", type=["xlsx", "xls"])

    if f1 and f2:
        df1 = pd.read_excel(uploaded_file1, engine="openpyxl")
        df2 = pd.read_excel(uploaded_file2, engine="openpyxl")

        st.divider()

        colA, colB = st.columns(2)
        with colA:
            st.write("表1预览")
            st.dataframe(df1.head(3), use_container_width=True)
        with colB:
            st.write("表2预览")
            st.dataframe(df2.head(3), use_container_width=True)

        st.markdown("#### 🔧 核心对账字段（必选）")
        col1, col2 = st.columns(2)
        with col1:
            col_key1 = st.selectbox("表1：匹配关联字段（发票号码）", df1.columns)
            col_amt1 = st.selectbox("表1：金额字段", df1.columns)
        with col2:
            col_key2 = st.selectbox("表2：匹配关联字段（发票号码）", df2.columns)
            col_amt2 = st.selectbox("表2：金额字段", df2.columns)

        st.markdown("#### 📎 附加展示字段（可选，勾选才带入结果）")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            add_cols1 = st.multiselect("表1额外字段", df1.columns, default=[])
        with col_s2:
            add_cols2 = st.multiselect("表2额外字段", df2.columns, default=[])

        run_btn = st.button("▶ 执行对账计算", key="run_tab1")
        if run_btn:
            # 重新对账，清空对话、待提问
            st.session_state.chat_history = []
            st.session_state.pending_question = ""
            df1 = df1.copy()
            df2 = df2.copy()
            df1[col_key1] = df1[col_key1].astype(str).str.strip()
            df2[col_key2] = df2[col_key2].astype(str).str.strip()

            merge_df = pd.merge(
                df1,
                df2,
                left_on=col_key1,
                right_on=col_key2,
                how="outer",
                indicator=True
            )
            merge_df["金额差异"] = merge_df[col_amt1] - merge_df[col_amt2]
            merge_df["匹配结果"] = merge_df["_merge"].map({
                "both": "两边匹配成功",
                "left_only": "仅存在于表1（有发票无凭证）",
                "right_only": "仅存在于表2（有凭证无发票）"
            })

            def mark_result(row):
                if row["匹配结果"] == "两边匹配成功":
                    if abs(row["金额差异"]) > 0.01:
                        return "⚠️金额不一致疑点"
                    else:
                        return "✅金额一致"
                else:
                    return "缺少对方匹配记录"

            merge_df["对账结论"] = merge_df.apply(mark_result, axis=1)
            doubt_df = merge_df[merge_df["对账结论"].str.contains("⚠️")].copy()

            # 存入session，按钮刷新不会丢
            st.session_state.merge_df = merge_df
            st.session_state.doubt_df = doubt_df
            st.session_state.current_doubt_text = doubt_df.to_string()

        # 只要已经算过对账，就展示看板和问答区
        if st.session_state.merge_df is not None:
            merge_df = st.session_state.merge_df
            doubt_df = st.session_state.doubt_df
            total_cnt = len(merge_df)
            doubt_cnt = len(doubt_df)

            st.divider()
            st.info(f"📊汇总：总记录 {total_cnt} 条，疑点 {doubt_cnt} 条")

            # Plotly交互式饼图
            st.subheader("对账分布看板")
            stat = merge_df["对账结论"].value_counts().reset_index()
            stat.columns = ["对账结论", "数量"]
            fig = px.pie(stat, values="数量", names="对账结论",
                         color="对账结论",
                         color_discrete_map={
                             "✅金额一致": "#27ae60",
                             "⚠️金额不一致疑点": "#e74c3c",
                             "缺少对方匹配记录": "#f39c12"
                         },
                         hole=0.1, width=600, height=600)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("完整对账结果")
            st.dataframe(merge_df, use_container_width=True)
            st.subheader("疑点清单")
            st.dataframe(doubt_df, use_container_width=True)

            # 自动AI疑点分析
            if enable_ai and not doubt_df.empty:
                st.subheader("🤖 DeepSeek AI 疑点自动分析")
                with st.spinner("AI正在解读风控疑点..."):
                    ai_result = ai_analysis(st.session_state.current_doubt_text, api_key)
                    st.markdown(ai_result)
            elif not enable_ai and not doubt_df.empty:
                st.info("💡 在左侧侧边栏填入DeepSeek API Key，开启AI功能")

            # ========== AI问答面板（修复快捷按钮） ==========
            st.divider()
            st.subheader("💬 针对本次对账疑点自由提问")
            st.caption("快捷提问（直接点）：")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.button("📝 核查通知", key="qbtn1", on_click=set_q1)
            with c2:
                st.button("📋 风控底稿描述", key="qbtn2", on_click=set_q2)
            with c3:
                st.button("🔍 审计取证思路", key="qbtn3", on_click=set_q3)
            with c4:
                st.button("📌 税务风险判断", key="qbtn4", on_click=set_q4)

            user_input = st.text_input("自定义问题：", placeholder="在这里输入你的问题，基于上面疑点数据提问", key="user_q_input")
            submit_custom = st.button("提交自定义问题")
            if submit_custom and user_input.strip() != "":
                st.session_state.pending_question = user_input.strip()

            # 处理待提问
            if st.session_state.pending_question and enable_ai:
                q = st.session_state.pending_question
                with st.spinner("AI思考中..."):
                    reply = ai_chat(q, st.session_state.current_doubt_text, st.session_state.chat_history, api_key)
                    st.session_state.chat_history.append({"role":"user", "content":q})
                    st.session_state.chat_history.append({"role":"assistant", "content":reply})
                st.markdown(f"👤 **你：** {q}")
                st.markdown(f"🤖 **AI：** {reply}")
                # 清空，防止反复调用
                st.session_state.pending_question = ""
            elif st.session_state.pending_question and not enable_ai:
                st.warning("⚠️请先在侧边栏填写DeepSeek API Key")
                st.session_state.pending_question = ""

            # 展示全部对话历史
            if st.session_state.chat_history:
                st.markdown("#### 📜 本次对话记录")
                for msg in st.session_state.chat_history:
                    if msg["role"] == "user":
                        st.markdown(f"👤 **你：** {msg['content']}")
                    else:
                        st.markdown(f"🤖 **AI：** {msg['content']}")

            buf_all = BytesIO()
            merge_df.to_excel(buf_all, index=False)
            st.download_button("下载全部对账结果", buf_all.getvalue(), "通用对账_全部结果.xlsx")
            buf_d = BytesIO()
            doubt_df.to_excel(buf_d, index=False)
            st.download_button("下载疑点清单", buf_d.getvalue(), "通用对账_疑点清单.xlsx")

# ===================== Tab2 银行流水对账 + 余额调节表 =====================
with tab2:
    st.subheader("银行流水对账 & 余额调节表")
    f_bank = st.file_uploader("上传银行对账单", type=["xlsx", "xls"])
    f_book = st.file_uploader("上传企业银行日记账", type=["xlsx", "xls"])
    if f_bank and f_book:
        df_bank = pd.read_excel(f_bank)
        df_book = pd.read_excel(f_book)
        st.write("银行对账单预览：", df_bank.head())
        st.write("企业日记账预览：", df_book.head())

        bank_balance = st.number_input("银行对账单期末余额", value=0.0)
        book_balance = st.number_input("企业账面期末余额", value=0.0)
        st.markdown("#### 未达账项录入")
        col1, col2 = st.columns(2)
        with col1:
            bank_add = st.number_input("银行已收企业未收", value=0.0)
            bank_sub = st.number_input("银行已付企业未付", value=0.0)
        with col2:
            book_add = st.number_input("企业已收银行未收", value=0.0)
            book_sub = st.number_input("企业已付银行未付", value=0.0)

        if st.button("生成余额调节表"):
            adj_bank = bank_balance + book_add - book_sub
            adj_book = book_balance + bank_add - bank_sub
            st.success(f"调节后银行余额：{adj_bank:.2f}，调节后账面余额：{adj_book:.2f}")
            if abs(adj_bank - adj_book) < 0.01:
                st.success("✅余额调节平衡！")
            else:
                st.error("⚠️调节不平衡，请核对未达账项")
            df_adj = pd.DataFrame({
                "项目":["银行对账单余额","+企业已收银行未收","-企业已付银行未付","调节后余额",
                        "企业账面余额","+银行已收企业未收","-银行已付企业未付","调节后余额"],
                "金额":[bank_balance, book_add, book_sub, adj_bank, book_balance, bank_add, bank_sub, adj_book]
            })
            st.dataframe(df_adj)
            buf = BytesIO()
            df_adj.to_excel(buf, index=False)
            st.download_button("下载余额调节表", buf.getvalue(), "银行余额调节表.xlsx")

# ===================== Tab3 应收台账｜账龄+信用风险监控 =====================
with tab3:
    st.subheader("应收台账 | 账龄计算 & 客户信用风险监控")
    f_rec = st.file_uploader("上传应收台账表（必须包含：客户名称、应收金额、到期日）", type=["xlsx", "xls"])
    if f_rec:
        df_rec = pd.read_excel(f_rec)
        st.dataframe(df_rec.head())
        today = pd.to_datetime(st.date_input("统计基准日期"))
        df_rec["到期日"] = pd.to_datetime(df_rec["到期日"], errors="coerce")
        df_rec["逾期天数"] = (today - df_rec["到期日"]).dt.days

        def risk_tag(day):
            if pd.isna(day):
                return "正常（未到期）"
            elif day <= 0:
                return "正常（未到期）"
            elif day <=30:
                return "🟡 逾期1-30天，低风险"
            elif day <=90:
                return "🟠 逾期31-90天，中风险"
            else:
                return "🔴 逾期90天以上，高风险"
        df_rec["风险等级"] = df_rec["逾期天数"].apply(risk_tag)
        st.subheader("应收账龄&风险结果")
        st.dataframe(df_rec, use_container_width=True)
        risk_stat = df_rec["风险等级"].value_counts().reset_index()
        risk_stat.columns = ["风险等级","数量"]
        fig_bar = px.bar(risk_stat, x="风险等级", y="数量", color="风险等级")
        st.plotly_chart(fig_bar, use_container_width=True)
        buf = BytesIO()
        df_rec.to_excel(buf, index=False)
        st.download_button("下载应收风险台账", buf.getvalue(), "应收客户信用风险台账.xlsx")
