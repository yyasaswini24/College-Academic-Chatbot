import sys
from pathlib import Path

import streamlit as st

# Make the project root importable so the frontend can use the backend package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.llm import ask_llm_stream
from backend.chat_store import delete_chat, list_chats, load_chat, new_chat_id, save_chat

st.set_page_config(
    page_title="College Academic Assistant",
    page_icon=":material/school:",
    layout="centered"
)

FRONTEND_DIR = Path(__file__).resolve().parent

# Custom styles and animations (light mode swaps the colour palette)
is_dark = st.context.theme.type != "light"
st.html(FRONTEND_DIR / "styles.css")
if not is_dark:
    st.html(FRONTEND_DIR / "styles-light.css")

HERO_HTML = """
<div class="hero">
  <div class="orb-wrap">
    <div class="orb">
      <div class="ring"></div>
      <div class="ring r2"></div>
      <span class="cap">🎓</span>
    </div>
  </div>
  <h1 class="hero-title"><span class="gradient-text">College academic assistant</span></h1>
  <div class="hero-sub">
    Your AI study buddy for
    <span class="rotator">
      <span>tricky concepts</span>
      <span>assignments</span>
      <span>exam prep</span>
      <span>coding doubts</span>
      <span>tricky concepts</span>
    </span>
  </div>
</div>
"""

MINI_HEADER_HTML = """
<div class="mini-header">
  <div class="mini-orb">🎓</div>
  <div class="mini-title gradient-text">College academic assistant</div>
</div>
"""

TYPING_HTML = '<div class="typing"><span></span><span></span><span></span></div>'

SUGGESTIONS = {
    ":blue[:material/psychology:] Explain machine learning": "Explain machine learning in simple terms with an example.",
    ":green[:material/functions:] Solve a math problem": "How do I find the derivative of x^2 * sin(x)? Show the steps.",
    ":orange[:material/menu_book:] Make study notes": "Give me short revision notes on the OSI model.",
    ":violet[:material/schedule:] Plan my exam prep": "Create a 7-day study plan for my data structures exam.",
}

USER_AVATAR = ":material/person:"
ASSISTANT_AVATAR = ":material/school:"

# Current chat: its messages and saved-file id (None until the first answer is saved).
# The open chat's id is kept in the URL (?chat=...) so it survives a page reload.
if "messages" not in st.session_state:
    url_chat_id = st.query_params.get("chat")
    st.session_state.messages = load_chat(url_chat_id) if url_chat_id else []
    st.session_state.chat_id = url_chat_id if st.session_state.messages else None


def new_chat():
    st.session_state.messages = []
    st.session_state.chat_id = None
    if "chat" in st.query_params:
        del st.query_params["chat"]


def open_chat(chat_id):
    st.session_state.messages = load_chat(chat_id)
    st.session_state.chat_id = chat_id
    st.query_params["chat"] = chat_id


def switch_theme(theme):
    # Streamlit has no Python API for this, so set the theme it remembers in the
    # browser (same as picking it in Settings) and reload the page
    st.html(
        f"""<script>
        localStorage.setItem("stActiveTheme-" + window.location.pathname + "-v2", JSON.stringify("{theme}"));
        window.location.reload();
        </script>""",
        unsafe_allow_javascript=True,
    )


def remove_chat(chat_id):
    delete_chat(chat_id)
    if st.session_state.chat_id == chat_id:
        new_chat()


# Sidebar
with st.sidebar:
    st.header("Academic assistant", icon=":material/school:")
    st.caption("Your study buddy for concepts, problems, notes and exam prep.")

    dark_mode = st.toggle(":material/dark_mode: Dark mode", value=is_dark, key=f"dark_mode_{is_dark}")
    if dark_mode != is_dark:
        switch_theme("Dark" if dark_mode else "Light")

    st.button(
        "New chat",
        key="new_chat",
        icon=":material/add_comment:",
        on_click=new_chat,
        type="primary",
        width="stretch",
        disabled=not st.session_state.messages,
    )

    st.subheader("Recent chats", icon=":material/history:")
    saved_chats = list_chats()
    if not saved_chats:
        st.caption("No saved chats yet. Your conversations will appear here.")

    for chat in saved_chats:
        is_current = chat["id"] == st.session_state.chat_id
        title_col, delete_col = st.columns([5, 1], gap="small", vertical_alignment="center")
        with title_col:
            st.button(
                chat["title"],
                key=f"open_{chat['id']}",
                icon=":material/chat_bubble:",
                on_click=open_chat,
                args=(chat["id"],),
                type="secondary" if is_current else "tertiary",
                width="stretch",
            )
        with delete_col:
            st.button(
                ":material/delete:",
                key=f"delete_{chat['id']}",
                help="Delete chat",
                on_click=remove_chat,
                args=(chat["id"],),
                type="tertiary",
            )

    st.space("medium")
    with st.expander("Tips", icon=":material/lightbulb:"):
        st.caption(
            "- Be specific: mention the subject and topic\n"
            "- Ask for examples or step-by-step solutions\n"
            "- Ask follow-ups to go deeper"
        )
    st.caption(":material/bolt: Powered by Google Gemini")

# Header: animated hero on an empty chat, compact header while chatting
suggested_prompt = None
if not st.session_state.messages:
    st.html(HERO_HTML)
    st.space("small")

    # Suggestion chips
    with st.container(key="suggestions", horizontal_alignment="center"):
        selected = st.pills(
            "Try asking",
            list(SUGGESTIONS.keys()),
            label_visibility="collapsed",
            key="suggestion",
        )
    if selected:
        suggested_prompt = SUGGESTIONS[selected]
else:
    st.html(MINI_HEADER_HTML)

# Display previous messages
for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else ASSISTANT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# User input
question = st.chat_input("Ask your academic question...", submit_mode="disable")
question = question or suggested_prompt

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(question)

    # Stream the AI response
    answered = False
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        try:
            # Bouncing dots until the first words arrive, then stream into the same spot
            placeholder = st.empty()
            placeholder.html(TYPING_HTML)
            stream = ask_llm_stream(st.session_state.messages)
            first_chunk = next(stream, "")

            def full_stream():
                yield first_chunk
                yield from stream

            answer = placeholder.write_stream(full_stream())
            st.session_state.messages.append({"role": "assistant", "content": answer})
            answered = True

        except Exception as e:
            st.error(f"Unable to get AI response: {e}", icon=":material/error:")

    # Save the chat and refresh the sidebar list
    if answered:
        if st.session_state.chat_id is None:
            st.session_state.chat_id = new_chat_id()
            st.query_params["chat"] = st.session_state.chat_id
        save_chat(st.session_state.chat_id, st.session_state.messages)
        st.rerun()
