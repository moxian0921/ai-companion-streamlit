import os
from openai import OpenAI
import streamlit as st
from datetime import datetime
import json

st.set_page_config(
    page_title="AI智能伴侣",
    page_icon="💝",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={}
)

# 生成会话标识函数
def generate_session_name():
    return datetime.now().strftime("%Y-%m-%d %H-%M-%S")

#保存会话信息的函数
def save_session():
    session_date = {
        "current_session": st.session_state.current_session,
        "messages": st.session_state.messages,
        "nick_name": st.session_state.nick_name,
        "nature": st.session_state.nature
    }
    if not os.path.exists("session"):
        os.makedirs("session")
    with open(f"session/{st.session_state.current_session}.json", "w", encoding="utf-8") as f:
        json.dump(session_date, f, ensure_ascii=False, indent=4)

#加载会话信息的函数
def load_session():
    session_list = []
    if os.path.exists("session"):
        file_list = os.listdir("session")
        for file_name in file_list:
            if file_name.endswith(".json"):
                session_list.append(file_name[:-5])
    session_list.sort(reverse=True)
    return session_list

def get_load_session(session_name):
    try:
        if os.path.exists(f"session/{session_name}.json"):
            with open(f"session/{session_name}.json", "r", encoding="utf-8") as f:
                session_date = json.load(f)
                st.session_state.messages = session_date["messages"]
                st.session_state.nick_name = session_date["nick_name"]
                st.session_state.nature = session_date["nature"]
                st.session_state.current_session = session_name
    except Exception as e:
        st.error(f"加载会话失败: {e}")

def delete_session(session_name):
    try:
        if os.path.exists(f"session/{session_name}.json"):
            os.remove(f"session/{session_name}.json")
            if session_name == st.session_state.current_session:
                st.session_state.messages = []
                st.session_state.current_session = generate_session_name()
    except Exception as e:
        st.error(f"删除会话失败: {e}")

#大标题
st.title("AI智能伴侣")
st.write("欢迎使用AI智能伴侣，您的个人助手！")

# ========= 暂时注释logo，避免部署缺失图片直接崩溃 =========
# logo_path = os.path.join(os.path.dirname(__file__), "resources", "img.png")
# st.logo(logo_path)

system_prompt = """
你叫%s，现在是用户的真实伴侣，请完全代入伴侣角色。
规则：
1. 每次只回1条消息
2. 禁止任何场景或状态描述性文字
3. 匹配用户的语言
4. 回复简短，像微信聊天一样
5. 有需要的话可以用❤️🌸等emoji表情
6. 用符合伴侣性格的方式对话
7. 回复的内容,要充分体现伴侣的性格特征
伴侣性格：
- %s
你必须严格遵守上述规则来回复用户。 
"""

if "messages" not in st.session_state:
    st.session_state.messages = []
if "nick_name" not in st.session_state:
    st.session_state.nick_name = "小甜甜"
if "nature" not in st.session_state:
    st.session_state.nature = "活泼开朗的东北姑娘"
if "current_session" not in st.session_state:
    now = generate_session_name()
    st.session_state.current_session = now

st.text(f"当前会话：{st.session_state.current_session}")

for message in st.session_state.messages:
    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    elif message["role"] == "assistant":
        st.chat_message("assistant").write(message["content"])

# 密钥检查
api_key = os.environ.get('DEEPSEEK_API_KEY')
if not api_key:
    st.error("未配置DEEPSEEK_API_KEY，请在Secrets中填写密钥！")
    st.stop()

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

with st.sidebar:
    st.subheader("AI控制面板")
    if st.button("新建会话",width="stretch",icon="🚀"):
        save_session()
        st.session_state.messages = []
        st.session_state.current_session = generate_session_name()
        # 不主动保存空会话，避免大量空json文件
        st.rerun()

    st.divider()
    st.text("会话历史")
    session_list = load_session()
    for session in session_list:
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            if st.button(session, width="stretch", icon="📑", key=f"load_{session}", type="primary" if session == st.session_state.current_session else "secondary"):
                get_load_session(session)
                st.rerun()
        with col2:
            if st.button("", width="stretch", icon="❌️", key=f"delete_{session}"):
                delete_session(session)
                st.rerun()

    st.subheader("伴侣的信息")
    nick_name = st.text_input("伴侣的名称",placeholder="请输入昵称",value=st.session_state.nick_name)
    if nick_name:
        st.session_state.nick_name = nick_name
    nature = st.text_area("伴侣的性格",placeholder="请输入性格",value=st.session_state.nature)
    if nature:
        st.session_state.nature = nature

prompt = st.chat_input("请输入您的问题：")
if prompt:
    st.chat_message("user").write(prompt)
    print("--------->调用AI大模型，提示词：", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system","content": system_prompt % (st.session_state.nick_name, st.session_state.nature)},
            *st.session_state.messages
        ],
        stream=True
    )
    #修复流式输出，只创建一次assistant框
    with st.chat_message("assistant"):
        response_message = st.empty()
        full_response = ""
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content is not None:
                full_response += delta.content
                response_message.write(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    save_session()
