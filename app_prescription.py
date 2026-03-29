import streamlit as st
import google.generativeai as genai
import datetime
import json
import os
import requests
import textwrap
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# ページ設定
st.set_page_config(page_title="美肌処方箋ジェネレーター | Luxia SaaS", layout="centered")

# --- 日本語フォントの自動取得と設定 ---
@st.cache_resource
def setup_japanese_font():
    font_path = "MPLUS1p-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://raw.githubusercontent.com/google/fonts/main/ofl/mplus1p/MPLUS1p-Regular.ttf"
        response = requests.get(url)
        if response.status_code == 200:
            with open(font_path, "wb") as f:
                f.write(response.content)
    pdfmetrics.registerFont(TTFont("MPLUS1p", font_path))
    return "MPLUS1p"

# --- UIのスタイリング ---
st.markdown("""
    <style>
    .prescription-box { border: 2px solid #555; padding: 25px; border-radius: 10px; background-color: #f9f9f9; margin-top: 20px; }
    .rx-title { color: #2c3e50; text-align: center; font-size: 32px; font-weight: bold; margin-bottom: 5px; }
    .rx-header { font-size: 16px; color: #555; text-align: right; }
    .product-name { font-weight: bold; color: #e67e22; font-size: 1.1em; }
    .salon-treatment { font-weight: bold; color: #2c3e50; font-size: 1.2em; border-bottom: 2px solid #e67e22; padding-bottom: 2px; }
    .usage-step { font-weight: bold; color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

def draw_wrapped_text(c, text, x, y, max_chars, line_height):
    lines = textwrap.wrap(text, width=max_chars)
    for line in lines:
        c.drawString(x, y, line)
        y -= line_height
    return y

# --- PDF生成関数 ---
def create_pdf(customer_name, staff_name, date_str, rx_data, font_name, salon_name):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    c.setFont(font_name, 10)
    c.drawRightString(width - 15*mm, height - 15*mm, f"診断日: {date_str}")
    c.drawRightString(width - 15*mm, height - 20*mm, f"担当スタッフ: {staff_name}")
    c.drawRightString(width - 15*mm, height - 25*mm, f"発行元: {salon_name}")
    
    c.setFont(font_name, 24)
    c.drawCentredString(width/2, height - 40*mm, "美肌処方箋 (Rx)")
    
    c.setFont(font_name, 16)
    c.drawString(20*mm, height - 55*mm, f"{customer_name} 専用ケアプラン")
    
    text_y = height - 70*mm
    
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "【プロフェッショナル・アドバイス】")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    advice = rx_data.get("advice", "")
    text_y = draw_wrapped_text(c, advice, 25*mm, text_y, max_chars=40, line_height=6*mm)
    
    text_y -= 5*mm
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "🌙 朝のケア (Morning)")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    for i, product in enumerate(rx_data.get("morning_routine_products", [])):
        text_y = draw_wrapped_text(c, f"STEP{i+1}: {product}", 25*mm, text_y, max_chars=40, line_height=6*mm)
        
    text_y -= 5*mm
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "☀️ 夜のケア (Evening)")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    for i, product in enumerate(rx_data.get("evening_routine_products", [])):
        text_y = draw_wrapped_text(c, f"STEP{i+1}: {product}", 25*mm, text_y, max_chars=40, line_height=6*mm)

    text_y -= 5*mm
    c.setFont(font_name, 14)
    c.drawString(20*mm, text_y, "💡 サロン推奨施術のご提案")
    text_y -= 8*mm
    c.setFont(font_name, 12)
    treatment = rx_data.get("recommended_salon_treatment", "")
    text_y = draw_wrapped_text(c, f"・ {treatment}", 25*mm, text_y, max_chars=40, line_height=6*mm)
    
    c.setFont(font_name, 10)
    c.drawCentredString(width/2, 20*mm, f"Copyright (C) {datetime.date.today().year} {salon_name} All Rights Reserved.")
    
    c.save()
    buffer.seek(0)
    return buffer

st.title("🛡️ AI 自動生成「美肌処方箋」ジェネレーター")
st.markdown("サロン専用のAIが、10項目の詳細なライフスタイル分析から最適なケアプランを提案します。")

st.sidebar.header("⚙️ 導入サロン用 初期設定")
salon_name = st.sidebar.text_input("サロン名（PDF発行元）", value="株式会社Luxia 美容研究所")
custom_treatments = st.sidebar.text_area(
    "自店の推奨施術メニュー（改行して複数入力）",
    value="・高濃度ビタミンC導入 (シミ、くすみ)\n・ハーブピーリング (毛穴、肌荒れ)\n・幹細胞フェイシャル (ハリ、小じわ)\n・ラジオ波フェイシャル (たるみ、むくみ)"
)

st.sidebar.divider()
st.sidebar.header("1. 顧客情報入力")
customer_name = st.sidebar.text_input("お客様名", value="山田 花子 様")
staff_name = st.sidebar.text_input("担当スタッフ", value="佐藤 美記")
counseling_date = st.sidebar.date_input("診断日", datetime.date.today())

st.sidebar.divider()
st.sidebar.header("2. 肌診断・お悩み入力")
skin_type = st.sidebar.selectbox("肌質", ["乾燥肌", "脂性肌", "混合肌", "普通肌", "敏感肌"])
main_concerns = st.sidebar.multiselect("主なお悩み (複数選択可)", ["乾燥・カサつき", "ニキビ・肌荒れ", "シミ・くすみ", "ハリ不足・小じわ", "毛穴の目立ち", "テカリ・べたつき"])

st.sidebar.divider()
st.sidebar.header("3. 生活習慣アンケート (全10問)")
ans_sleep = st.sidebar.selectbox("Q1. 睡眠状況", ["特に問題なし", "6時間未満", "不規則", "眠りが浅い"])
ans_diet = st.sidebar.selectbox("Q2. 食生活", ["特に問題なし", "甘いものをよく食べる", "脂っこいものをよく食べる", "外食が多い"])
ans_env = st.sidebar.selectbox("Q3. 日中の環境", ["特に問題なし", "エアコンの効いた室内に長時間いる", "屋外にいることが多い", "PC/スマホを長時間見る"])
ans_excercise = st.sidebar.selectbox("Q4. 運動・入浴", ["週に数回運動する", "全く運動しない", "シャワーだけで済ませることが多い", "湯船に浸かる"])
ans_skincare = st.sidebar.selectbox("Q5. スキンケア習慣", ["丁寧に保湿している", "クレンジングはオイル派", "ダブル洗顔をしている", "とにかく時短で済ませたい"])
# --- 新規追加の5問 ---
ans_stress = st.sidebar.selectbox("Q6. ストレス・疲労感", ["特に感じない", "日常的にストレスがある", "疲れが顔に出やすい", "常に疲労感がある"])
ans_water = st.sidebar.selectbox("Q7. 1日の水分補給", ["水・お茶を1.5L以上飲む", "主にコーヒーや紅茶を飲む", "あまり水分を摂らない"])
ans_uv = st.sidebar.selectbox("Q8. 紫外線対策", ["1年を通して対策している", "夏場や外出時のみ対策する", "あまり対策していない"])
ans_cycle = st.sidebar.selectbox("Q9. 肌のゆらぎ・周期", ["常に安定している", "生理前に荒れやすい", "季節の変わり目に敏感になる", "常に不安定"])
ans_goal = st.sidebar.selectbox("Q10. 目指す理想の肌", ["透明感のある発光肌", "たるみのないハリツヤ肌", "トラブルのないなめらか肌", "毛穴レスな陶器肌"])

questionnaire_summary = f"""
- 睡眠: {ans_sleep}
- 食事: {ans_diet}
- 環境: {ans_env}
- 運動: {ans_excercise}
- ケア: {ans_skincare}
- ストレス: {ans_stress}
- 水分補給: {ans_water}
- 紫外線対策: {ans_uv}
- 肌のゆらぎ: {ans_cycle}
- 理想の肌: {ans_goal}
"""

st.sidebar.divider()
st.sidebar.header("4. API設定")
# 1. サーバー側に保存されたキーを探し、なければ空文字を入れる
default_key = st.secrets.get("GEMINI_API_KEY", "")

# 2. 入力欄の初期値にそのキーを設定する（手入力も可能にする）
api_key = st.sidebar.text_input("Gemini APIキーを入力", value=default_key, type="password")

st.sidebar.divider()
st.sidebar.header("5. 処方箋の発行")
generate_btn = st.sidebar.button("AI 美肌処方箋を生成する")

if generate_btn:
    if not api_key: st.error("APIキーを入力してください")
    elif not main_concerns: st.error("主なお悩みを1つ以上選択してください。")
    else:
        with st.spinner("10項目の詳細データをAIが解析中..."):
            try:
                font_name = setup_japanese_font()
                genai.configure(api_key=api_key)
                
                system_instruction = f"""
                あなたは日本のサロン専属トップエステティシャンです。顧客の全10項目の詳細なライフスタイルデータを深く分析し、以下のJSON形式で出力してください。
                ```json
                {{
                  "advice": "顧客の悩み、生活習慣、そして『目指す理想の肌』を統合分析した、寄り添いと説得力のある美容アドバイス（120文字程度）。",
                  "morning_routine_products": ["製品A (使い方)"],
                  "evening_routine_products": ["製品B (使い方)"],
                  "recommended_salon_treatment": "最も効果的なサロン施術名1つとその論理的な理由"
                }}
                ```
                製品情報:
                - ROMAN スキンケアローション (基礎保湿)
                - NIVORA クリアバランシングセラム (ニキビ、肌荒れ、毛穴、脂性肌向け)
                - NIVORA リッチモイスチャークリーム (乾燥、小じわ、ハリ不足向け)
                
                導入サロンの施術メニュー（必ず以下の選択肢から、顧客の悩みと生活習慣に最も合うものを1つだけ選んで提案してください）:
                {custom_treatments}
                
                ルール: 朝夜のSTEP1は必ずROMANスキンケアローション。夜のSTEP2以降は悩み応じてNIVORAを追加。
                """
                user_prompt = f"お客様名: {customer_name}\n肌質: {skin_type}\n主なお悩み: {', '.join(main_concerns)}\n生活習慣詳細データ:\n{questionnaire_summary}"
                
                model = genai.GenerativeModel(model_name="gemini-2.5-flash", system_instruction=system_instruction)
                response = model.generate_content(user_prompt)
                
                json_text = response.text.replace('```json\n', '').replace('\n```', '')
                rx_data = json.loads(json_text)
                
                pdf_file = create_pdf(customer_name, staff_name, str(counseling_date), rx_data, font_name, salon_name)
                
                st.divider()
                st.success("✅ 処方箋の生成が完了しました！下のボタンからPDFをダウンロードできます。")
                
                st.download_button(
                    label="📥 美肌処方箋をPDFでダウンロード (LINE送付用)",
                    data=pdf_file,
                    file_name=f"{customer_name.replace(' 様', '')}_美肌処方箋.pdf",
                    mime="application/pdf",
                    type="primary"
                )

                st.markdown("<div class='prescription-box'>", unsafe_allow_html=True)
                st.markdown("<p class='rx-title'>美肌処方箋 (Rx)</p>", unsafe_allow_html=True)
                st.markdown(f"<div class='rx-header'>診断日: {counseling_date}<br>担当スタッフ: {staff_name}<br>発行元: {salon_name}</div>", unsafe_allow_html=True)
                st.subheader(f"✨ {customer_name} 専用ケアプラン")
                st.info(rx_data.get("advice", ""))
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🌙 朝のケア")
                    for i, p in enumerate(rx_data.get("morning_routine_products", [])): st.markdown(f"- <span class='usage-step'>STEP{i+1}</span>: {p}", unsafe_allow_html=True)
                with col2:
                    st.subheader("☀️ 夜のケア")
                    for i, p in enumerate(rx_data.get("evening_routine_products", [])): st.markdown(f"- <span class='usage-step'>STEP{i+1}</span>: {p}", unsafe_allow_html=True)
                
                st.divider()
                st.subheader("💡 サロン推奨施術のご提案")
                st.markdown(f"- <span class='salon-treatment'>{rx_data.get('recommended_salon_treatment', '')}</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")