import streamlit as st

st.set_page_config(page_title="Test App")

st.title("Hello, SageAI Developer!")
st.success("If you can see this text, your Streamlit installation is working correctly.")

if 'count' not in st.session_state:
    st.session_state.count = 0

if st.button("Click Me"):
    st.session_state.count += 1

st.write(f"Button has been clicked {st.session_state.count} times.")