import io
import base64
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template, request
from sqlalchemy import create_engine

app = Flask(__name__)

# Ваше рабочее подключение к базе данных
DB_URI = 'postgresql+psycopg2://postgres:student@127.0.0.1:5436/nutrition_db'
ENGINE = create_engine(DB_URI)

def create_base64_plot(fig):
    """Вспомогательная функция для конвертации графика в строку base64"""
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    plt.close(fig)
    return base64.b64encode(img.getvalue()).decode('utf8')

@app.route('/')
def index():
    # Проверяем, нажал ли пользователь кнопку (есть ли в URL ?action=plot)
    action = request.args.get('action')
    
    # Строгий SQL-запрос только по существующим базовым колонкам
    query = """
        SELECT p.name, c.name as category, 
               p.calories, p.protein, p.fat, p.carbs
        FROM products p
        JOIN categories c ON p.category_id = c.id
    """
    df = pd.read_sql(query, ENGINE)
    
    products_json = df.to_json(orient='records')
    product_names = df['name'].tolist()

    # Умная статистика (сбор данных)
    stats_data = []
    metrics_map = {'calories': 'Калории (ккал)', 'protein': 'Белки (г)', 'fat': 'Жиры (г)', 'carbs': 'Углеводы (г)'}
    
    for col, name in metrics_map.items():
        mean_val = round(df[col].mean(), 1)
        median_val = round(df[col].median(), 1)
        
        max_idx = df[col].idxmax()
        min_idx = df[col].idxmin()
        
        max_str = f"{df.loc[max_idx, col]} ({df.loc[max_idx, 'name']})"
        min_str = f"{df.loc[min_idx, col]} ({df.loc[min_idx, 'name']})"
        
        stats_data.append({
            'Показатель': name,
            'Среднее': mean_val,
            'Медиана': median_val,
            'Абсолютный Минимум': min_str,
            'Абсолютный Максимум': max_str
        })
        
    stats_df = pd.DataFrame(stats_data)
    stats_html = stats_df.to_html(classes='table', index=False)

    top_protein = df.nlargest(5, 'protein')[['name', 'protein']]
    top_protein.columns = ['Продукт', 'Белки (г)']
    top_protein_html = top_protein.to_html(classes='table', index=False)

    high_cal = df.nlargest(5, 'calories')[['name', 'calories']]
    high_cal.columns = ['Продукт', 'Калории']
    high_cal_html = high_cal.to_html(classes='table', index=False)

    # 1. Изначально графиков НЕТ
    plot_bar = None
    plot_macro_profile = None

    # 2. Строим графики ТОЛЬКО если пришел сигнал от кнопки
    if action == 'plot':
        plt.style.use('bmh')

        # График 1: БЖУ на 100г
        fig_bar, ax1 = plt.subplots(figsize=(8, 5))
        grouped = df.groupby('category')[['protein', 'fat', 'carbs']].mean()
        grouped.columns = ['Белки', 'Жиры', 'Углеводы']
        grouped.plot(kind='bar', ax=ax1, color=['#3498db', '#f1c40f', '#2ecc71'], alpha=0.8)
        ax1.set_ylabel('БЖУ на 100г (г)')
        ax1.set_xlabel('')
        plt.xticks(rotation=45, ha='right')
        plot_bar = create_base64_plot(fig_bar)

        # График 2: Химический профиль (Доля макронутриентов)
        fig_macro, ax2 = plt.subplots(figsize=(8, 5))
        grouped_pct = grouped.div(grouped.sum(axis=1), axis=0) * 100
        grouped_pct.plot(kind='bar', stacked=True, ax=ax2, color=['#3498db', '#f1c40f', '#2ecc71'], alpha=0.85)
        ax2.set_ylabel('Доля в составе (%)')
        ax2.set_xlabel('')
        ax2.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=3)
        plt.xticks(rotation=45, ha='right')
        plot_macro_profile = create_base64_plot(fig_macro)

    # 3. Передаем данные в HTML-шаблон
    return render_template(
        'index.html', 
        total_records=len(df),
        products_json=products_json,
        product_names=sorted(product_names),
        stats_html=stats_html,
        top_protein_html=top_protein_html,
        high_cal_html=high_cal_html,
        plot_bar=plot_bar,
        plot_macro_profile=plot_macro_profile
    )

if __name__ == '__main__':
    print(">>> ПРОЕКТ ЗАПУЩЕН! Откройте http://127.0.0.1:8080", flush=True)
    app.run(host='0.0.0.0', port=8080)