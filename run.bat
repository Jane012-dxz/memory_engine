@echo off
chcp 65001 >nul
set DEEPSEEK_API_KEY=bd027701718f4404876494c89f6d0bba.kQOej6ydUiYMvI3R
set DEEPSEEK_BASE_URL=https://open.bigmodel.cn/api/paas/v4
set DEEPSEEK_MODEL=glm-4-flash
call .venv\Scripts\activate.bat
streamlit run ui/streamlit_app.py
pause
