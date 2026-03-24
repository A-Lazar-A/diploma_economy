from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import tomllib

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Экономика дипломного проекта",
    page_icon=":material/table_chart:",
    layout="wide",
)


WORK_COLUMNS = ["№ этапа", "Название работы", "T_min", "T_max", "Исполнитель"]
SALARY_COLUMNS = ["Исполнитель", "Оклад"]
EQUIPMENT_COLUMNS = ["Название", "Кол-во", "Цена", "Срок амортизации в днях"]
LOCAL_DEFAULTS_PATH = Path(__file__).with_name("local_defaults.toml")


def load_local_defaults() -> dict:
    if not LOCAL_DEFAULTS_PATH.exists():
        return {}
    with LOCAL_DEFAULTS_PATH.open("rb") as file:
        return tomllib.load(file)


def default_works_df() -> pd.DataFrame:
    config = load_local_defaults()
    works = config.get("works", [])
    if works:
        return pd.DataFrame(works, columns=WORK_COLUMNS).reset_index(drop=True)
    return pd.DataFrame(
        [
            {
                "№ этапа": 1,
                "Название работы": "Сбор требований",
                "T_min": 8,
                "T_max": 16,
                "Исполнитель": "Аналитик",
            },
            {
                "№ этапа": 1,
                "Название работы": "Проектирование решения",
                "T_min": 16,
                "T_max": 24,
                "Исполнитель": "Инженер",
            },
        ],
        columns=WORK_COLUMNS,
    ).reset_index(drop=True)


def default_equipment_df() -> pd.DataFrame:
    config = load_local_defaults()
    equipment = config.get("equipment", [])
    if equipment:
        return pd.DataFrame(equipment, columns=EQUIPMENT_COLUMNS).reset_index(drop=True)
    return pd.DataFrame(
        [
            {
                "Название": "ПК",
                "Кол-во": 1,
                "Цена": 70000,
                "Срок амортизации в днях": 1095,
            }
        ],
        columns=EQUIPMENT_COLUMNS,
    ).reset_index(drop=True)


def init_state() -> None:
    config = load_local_defaults()
    if "works_seed" not in st.session_state:
        st.session_state.works_seed = default_works_df()
    if "equipment_seed" not in st.session_state:
        st.session_state.equipment_seed = default_equipment_df()
    if "salary_store" not in st.session_state:
        st.session_state.salary_store = config.get("salary_store", {"Аналитик": 80000.0, "Инженер": 90000.0})
    if "latex_output" not in st.session_state:
        st.session_state.latex_output = ""


def to_int(value: object, default: int = 0) -> int:
    try:
        if value is None or pd.isna(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def clean_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalize_works_df(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy().reset_index(drop=True)
    for column in WORK_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = ""
    prepared = prepared[WORK_COLUMNS]
    prepared["№ этапа"] = prepared["№ этапа"].apply(lambda x: max(to_int(x, 1), 1))
    prepared["Название работы"] = prepared["Название работы"].apply(clean_text)
    prepared["T_min"] = prepared["T_min"].apply(to_int)
    prepared["T_max"] = prepared["T_max"].apply(to_int)
    prepared["Исполнитель"] = prepared["Исполнитель"].apply(clean_text)
    prepared = prepared[
        (prepared["Название работы"] != "")
        | (prepared["Исполнитель"] != "")
        | (prepared["T_min"] > 0)
        | (prepared["T_max"] > 0)
    ].copy()
    return prepared.reset_index(drop=True)


def normalize_equipment_df(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy().reset_index(drop=True)
    for column in EQUIPMENT_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = ""
    prepared = prepared[EQUIPMENT_COLUMNS]
    prepared["Название"] = prepared["Название"].apply(clean_text)
    prepared["Кол-во"] = prepared["Кол-во"].apply(to_int)
    prepared["Цена"] = prepared["Цена"].apply(to_float)
    prepared["Срок амортизации в днях"] = prepared["Срок амортизации в днях"].apply(lambda x: max(to_int(x, 1), 1))
    prepared = prepared[
        (prepared["Название"] != "")
        | (prepared["Кол-во"] > 0)
        | (prepared["Цена"] > 0)
        | (prepared["Срок амортизации в днях"] > 0)
    ].copy()
    return prepared.reset_index(drop=True)


def calculate_works(df: pd.DataFrame) -> pd.DataFrame:
    works = normalize_works_df(df)
    if works.empty:
        result = works.copy()
        result["№ работы"] = pd.Series(dtype="int64")
        result["T_h"] = pd.Series(dtype="float64")
        result["T_d"] = pd.Series(dtype="float64")
        return result

    result = works.copy()
    result["№ работы"] = range(1, len(result) + 1)
    result["T_h"] = ((3 * result["T_min"] + 2 * result["T_max"]) / 5).round(1)
    result["T_d"] = (result["T_h"] / 8).round(2)
    return result


def build_salary_editor_df(workers: list[str], salary_store: dict[str, float]) -> pd.DataFrame:
    rows = [{"Исполнитель": worker, "Оклад": salary_store.get(worker, 0.0)} for worker in workers]
    return pd.DataFrame(rows, columns=SALARY_COLUMNS).reset_index(drop=True)


def update_salary_store(df: pd.DataFrame) -> None:
    salary_store: dict[str, float] = {}
    if not df.empty:
        for _, row in df.iterrows():
            worker = clean_text(row.get("Исполнитель"))
            if worker:
                salary_store[worker] = to_float(row.get("Оклад"))
    st.session_state.salary_store = salary_store


def build_table_1_df(works_df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "№ этапа": works_df.get("№ этапа", pd.Series(dtype="int64")),
            "№ работы": works_df.get("№ работы", pd.Series(dtype="int64")),
            "Содержание работы": works_df.get("Название работы", pd.Series(dtype="object")),
            "T_min (чел/часы)": works_df.get("T_min", pd.Series(dtype="int64")),
            "T_max (чел/часы)": works_df.get("T_max", pd.Series(dtype="int64")),
            "T (чел/часы)": works_df.get("T_h", pd.Series(dtype="float64")),
            "T (чел/дни)": works_df.get("T_d", pd.Series(dtype="float64")),
            "Трудовые ресурсы": works_df.get("Исполнитель", pd.Series(dtype="object")),
        }
    ).reset_index(drop=True)


def build_table_2_df(works_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = [
        {
            "№": 1,
            "Событие": "Начало работ",
            "Работа": "",
            "Трудоёмкость (чел/часы)": "",
            "Трудоёмкость (чел/дни)": "",
            "Код работы": "",
            "Вид связи": "",
            "Ресурсы": "",
            "_row_type": "event",
            "_stage": "",
        }
    ]

    global_counter = 2
    prev_work_id = 1
    first_work = True

    for stage_no, stage_df in works_df.groupby("№ этапа", sort=True):
        rows.append(
            {
                "№": global_counter,
                "Событие": f"Этап {stage_no}",
                "Работа": "",
                "Трудоёмкость (чел/часы)": "",
                "Трудоёмкость (чел/дни)": "",
                "Код работы": "",
                "Вид связи": "",
                "Ресурсы": "",
                "_row_type": "event",
                "_stage": stage_no,
            }
        )
        global_counter += 1

        for _, row in stage_df.iterrows():
            code = str(global_counter) if first_work else f"{prev_work_id}-{global_counter}"
            rows.append(
                {
                    "№": global_counter,
                    "Событие": "",
                    "Работа": row["Название работы"],
                    "Трудоёмкость (чел/часы)": row["T_h"],
                    "Трудоёмкость (чел/дни)": row["T_d"],
                    "Код работы": code,
                    "Вид связи": "ОН",
                    "Ресурсы": f"{row['Исполнитель']}, ПК",
                    "_row_type": "work",
                    "_stage": stage_no,
                }
            )
            prev_work_id = global_counter
            global_counter += 1
            first_work = False

        rows.append(
            {
                "№": global_counter,
                "Событие": f"Этап {stage_no} завершен",
                "Работа": "",
                "Трудоёмкость (чел/часы)": "",
                "Трудоёмкость (чел/дни)": "",
                "Код работы": "",
                "Вид связи": "",
                "Ресурсы": "",
                "_row_type": "event",
                "_stage": stage_no,
            }
        )
        global_counter += 1

    return pd.DataFrame(rows).reset_index(drop=True)


def build_table_3_df(table_2_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    cumulative_days = 0.0

    work_rows = table_2_df[table_2_df["_row_type"] == "work"].reset_index(drop=True)
    for _, row in work_rows.iterrows():
        days = round(to_float(row["Трудоёмкость (чел/дни)"]), 2)
        cumulative_days = round(cumulative_days + days, 2)
        rows.append(
            {
                "№ этапа": row["_stage"],
                "Код работы": row["Код работы"],
                "T_{i-j} (чел/дни)": days,
                "T_i^P (чел/дни)": cumulative_days,
                "T_i^П (чел/дни)": cumulative_days,
                "R_i (чел/дни)": 0,
                "R_{i-j}^П (чел/дни)": 0,
                "R_{i-j}^С (чел/дни)": 0,
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "№ этапа",
            "Код работы",
            "T_{i-j} (чел/дни)",
            "T_i^P (чел/дни)",
            "T_i^П (чел/дни)",
            "R_i (чел/дни)",
            "R_{i-j}^П (чел/дни)",
            "R_{i-j}^С (чел/дни)",
        ],
    ).reset_index(drop=True)


def build_table_4_df(works_df: pd.DataFrame, salary_editor_df: pd.DataFrame) -> pd.DataFrame:
    if salary_editor_df.empty:
        return pd.DataFrame(
            columns=[
                "Исполнитель",
                "Оклад",
                "Оклад с налогами",
                "Дневной оклад",
                "Затраты времени (дни)",
                "Итого ЗП",
            ]
        )

    time_by_worker = works_df.groupby("Исполнитель")["T_d"].sum().to_dict() if not works_df.empty else {}
    table = salary_editor_df.copy().reset_index(drop=True)
    table["Исполнитель"] = table["Исполнитель"].apply(clean_text)
    table["Оклад"] = table["Оклад"].apply(to_float)
    table["Оклад с налогами"] = (table["Оклад"] * 1.13).round(2)
    table["Дневной оклад"] = ((table["Оклад с налогами"] * 8) / 165).round(2)
    table["Затраты времени (дни)"] = table["Исполнитель"].map(lambda x: round(to_float(time_by_worker.get(x, 0.0)), 2))
    table["Итого ЗП"] = (table["Дневной оклад"] * table["Затраты времени (дни)"]).round(2)
    return table


def build_table_5_df(equipment_df: pd.DataFrame, total_project_days: float) -> pd.DataFrame:
    if equipment_df.empty:
        return pd.DataFrame(columns=["Название", "Кол-во", "Цена", "Срок амортизации в днях", "Амортизация"])

    table = equipment_df.copy().reset_index(drop=True)
    table["Амортизация"] = table.apply(
        lambda row: round(((row["Цена"] * row["Кол-во"]) / max(row["Срок амортизации в днях"], 1)) * total_project_days, 2),
        axis=1,
    )
    return table


def build_table_6_df(table_4_df: pd.DataFrame, table_5_df: pd.DataFrame) -> pd.DataFrame:
    salary_total = round(to_float(table_4_df["Итого ЗП"].sum()) if not table_4_df.empty else 0.0, 2)
    overhead = round(salary_total * 0.6, 2)
    amortization = round(to_float(table_5_df["Амортизация"].sum()) if not table_5_df.empty else 0.0, 2)
    total = round(salary_total + overhead + amortization, 2)
    return pd.DataFrame(
        {
            "Статья": ["Зарплаты", "Накладные расходы (60% от Зарплат)", "Амортизация", "Итого"],
            "Сумма": [salary_total, overhead, amortization, total],
        }
    ).reset_index(drop=True)


def format_number(value: object) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.2f}".rstrip("0").rstrip(".")
    try:
        normalized = Decimal(str(value)).normalize()
        return format(normalized, "f").rstrip("0").rstrip(".") or "0"
    except (InvalidOperation, ValueError):
        return str(value)


def latex_escape(value: object) -> str:
    text = format_number(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    visible_df = df[[column for column in df.columns if not column.startswith("_")]].copy()
    for column in visible_df.columns:
        visible_df[column] = visible_df[column].map(format_number)
    return visible_df.reset_index(drop=True)


def wrap_longtable(lines: list[str]) -> str:
    return "\n".join(["{", *lines, "}"])


def build_table_1_latex(table_1_df: pd.DataFrame) -> str:
    rows: list[str] = []
    grouped = table_1_df.groupby("№ этапа", sort=True)
    for _, stage_df in grouped:
        stage_rows = stage_df.reset_index(drop=True)
        span = len(stage_rows)
        for idx, (_, row) in enumerate(stage_rows.iterrows()):
            stage_cell = rf"\multirow{{{span}}}{{*}}{{{latex_escape(row['№ этапа'])}}}" if idx == 0 else ""
            rows.append(
                " & ".join(
                    [
                        stage_cell,
                        latex_escape(row["№ работы"]),
                        latex_escape(row["Содержание работы"]),
                        latex_escape(row["T_min (чел/часы)"]),
                        latex_escape(row["T_max (чел/часы)"]),
                        latex_escape(row["T (чел/часы)"]),
                        latex_escape(row["T (чел/дни)"]),
                        latex_escape(row["Трудовые ресурсы"]),
                    ]
                )
                + (r" \\ \hhline{~-------}" if idx < span - 1 else r" \\ \hline")
            )

    if not rows:
        rows = [r"\multicolumn{8}{|c|}{Нет данных} \\ \hline"]

    return wrap_longtable(
        [
            r"\fontsize{10}{10}\selectfont",
            r"\setlength{\tabcolsep}{3pt}",
            "",
            r"\begin{longtable}{|c|c|p{4cm}|p{1.6cm}|p{1.6cm}|p{1.5cm}|p{1.6cm}|p{2.5cm}|}",
            r"\caption{Оценка трудоемкости работ проекта}\label{tab:tab2} \\",
            r"\hline",
            r"№ этапа & № работы & Содержание работы & T\_min (чел/час) & T\_max (чел/час) & T\newline(чел/час) & T\newline(чел/дни) & Трудовые ресурсы \\ \hline",
            r"\endfirsthead",
            "",
            r"\caption*{Продолжение таблицы \ref{tab:tab2}}\\ \hline",
            r"№ этапа & № работы & Содержание работы & T\_min (чел/час) & T\_max (чел/час) & T (чел/час) & T (чел/дни) & Трудовые ресурсы \\ \hline",
            r"\endhead",
            "",
            r"\hline",
            r"\endfoot",
            "",
            r"\hline",
            r"\endlastfoot",
            "",
            *rows,
            "",
            r"\end{longtable}",
        ]
    )


def build_table_2_latex(table_2_df: pd.DataFrame) -> str:
    rows = []
    for _, row in table_2_df.iterrows():
        rows.append(
            " & ".join(
                [
                    latex_escape(row["№"]),
                    latex_escape(row["Событие"]),
                    latex_escape(row["Работа"]),
                    latex_escape(row["Трудоёмкость (чел/часы)"]),
                    latex_escape(row["Трудоёмкость (чел/дни)"]),
                    latex_escape(row["Код работы"]),
                    latex_escape(row["Вид связи"]),
                    latex_escape(row["Ресурсы"]),
                ]
            )
            + r" \\ \hline"
        )

    if not rows:
        rows = [r"\multicolumn{8}{|c|}{Нет данных} \\ \hline"]

    return wrap_longtable(
        [
            r"\fontsize{12}{14}\selectfont",
            r"\setlength{\tabcolsep}{3pt}",
            "",
            r"\begin{longtable}{|c|p{2.3cm}|p{4.1cm}|p{1.5cm}|p{1.5cm}|p{1.2cm}|p{1.2cm}|p{2.9cm}|}",
            r"\caption{Соответствие событий и работ}\label{tab:tab3} \\",
            r"\hline",
            r"№ & Событие & Работа & Т (ч) & Т (дн) & Код  & Вид & Исполнитель \\ \hline",
            r"\endfirsthead",
            "",
            r"\caption*{Продолжение таблицы \ref{tab:tab3}}\\ \hline",
            r"№ & Событие & Работа & Т (ч) & Т (дн) & Код  & Вид & Исполнитель \\ \hline",
            r"\endhead",
            "",
            r"\hline",
            r"\endfoot",
            "",
            r"\hline",
            r"\endlastfoot",
            "",
            *rows,
            "",
            r"\end{longtable}",
        ]
    )


def build_table_3_latex(table_3_df: pd.DataFrame) -> str:
    rows = [
        " & ".join(
            [
                latex_escape(row["№ этапа"]),
                latex_escape(row["Код работы"]),
                latex_escape(row["T_{i-j} (чел/дни)"]),
                latex_escape(row["T_i^P (чел/дни)"]),
                latex_escape(row["T_i^П (чел/дни)"]),
                latex_escape(row["R_i (чел/дни)"]),
                latex_escape(row["R_{i-j}^П (чел/дни)"]),
                latex_escape(row["R_{i-j}^С (чел/дни)"]),
            ]
        )
        + r" \\ \hline"
        for _, row in table_3_df.iterrows()
    ]
    if not rows:
        rows = [r"\multicolumn{8}{|c|}{Нет данных} \\ \hline"]

    return wrap_longtable(
        [
            r"% \fontsize{10}{10}\selectfont",
            r"% \setlength{\tabcolsep}{3pt}",
            r"% \small",
            "",
            r"\begin{longtable}{|c|c|p{1.6cm}|p{1.6cm}|p{1.6cm}|c|c|c|}",
            r"\caption{Параметры сетевого графа}\label{tab:tab4} \\",
            r"\hline",
            r"№ этапа & Код работы & $T_{i-j}$ & $T_i^{P}$ & $T_i^{П}$ & $R_i$ & $R_{i-j}^{П}$  & $R_{i-j}^{С}$ \\ \hline",
            r"\endfirsthead",
            "",
            r"\caption*{Продолжение таблицы \ref{tab:tab4}}\\ \hline",
            r"№ этапа & Код работы & $T_{i-j}$ & $T_i^{P}$ & $T_i^{П}$ & $R_i$ & $R_{i-j}^{П}$ & $R_{i-j}^{С}$ \\ \hline",
            r"\endhead",
            "",
            r"\hline",
            r"\endfoot",
            "",
            r"\hline",
            r"\endlastfoot",
            "",
            *rows,
            "",
            r"\end{longtable}",
        ]
    )


def build_table_4_latex(table_4_df: pd.DataFrame) -> str:
    rows = [
        " & ".join(
            [
                latex_escape(row["Исполнитель"]),
                latex_escape(row["Оклад"]),
                latex_escape(row["Оклад с налогами"]),
                latex_escape(row["Дневной оклад"]),
                latex_escape(row["Затраты времени (дни)"]),
                latex_escape(row["Итого ЗП"]),
            ]
        )
        + r" \\ \hline"
        for _, row in table_4_df.iterrows()
    ]
    if not rows:
        rows = [r"\multicolumn{6}{|c|}{Нет данных} \\ \hline"]

    return wrap_longtable(
        [
            r"% \fontsize{10}{10}\selectfont",
            r"% \setlength{\tabcolsep}{3pt}",
            "",
            r"\begin{longtable}{|p{3.2cm}|c|p{2.2cm}|p{2.2cm}|p{2.4cm}|p{2.4cm}|}",
            r"\caption{Расчет заработной платы}\label{tab:tab5} \\",
            r"\hline",
            r"Исполнитель & Оклад & Оклад \newline с налогами & Дневной \newline оклад & Затраты \newline времени (дни) & Итого ЗП \\ \hline",
            r"\endfirsthead",
            "",
            r"\caption*{Продолжение таблицы \ref{tab:tab5}}\\ \hline",
            r"Исполнитель & Оклад & Оклад \newline с налогами & Дневной \newline оклад & Затраты \newline времени (дни) & Итого ЗП \\ \hline",
            r"\endhead",
            "",
            r"\hline",
            r"\endfoot",
            "",
            r"\hline",
            r"\endlastfoot",
            "",
            *rows,
            "",
            r"\end{longtable}",
        ]
    )


def build_table_5_latex(table_5_df: pd.DataFrame) -> str:
    rows = [
        " & ".join(
            [
                latex_escape(row["Название"]),
                latex_escape(row["Кол-во"]),
                latex_escape(row["Цена"]),
                latex_escape(row["Срок амортизации в днях"]),
                latex_escape(row["Амортизация"]),
            ]
        )
        + r" \\ \hline"
        for _, row in table_5_df.iterrows()
    ]
    if not rows:
        rows = [r"\multicolumn{5}{|c|}{Нет данных} \\ \hline"]

    return wrap_longtable(
        [
            "",
            r"\begin{longtable}{|c|c|c|c|c|}",
            r"\caption{Затраты на оборудование}\label{tab:tab6} \\",
            r"\hline",
            r"Название & Кол-во & Цена & Срок амортизации \newline в днях & Амортизация \\ \hline",
            r"\endfirsthead",
            "",
            r"\caption*{Продолжение таблицы \ref{tab:tab6}}\\ \hline",
            r"Название & Кол-во & Цена & Срок амортизации \newline в днях & Амортизация \\ \hline",
            r"\endhead",
            "",
            r"\hline",
            r"\endfoot",
            "",
            r"\hline",
            r"\endlastfoot",
            "",
            *rows,
            "",
            r"\end{longtable}",
        ]
    )


def build_table_6_latex(table_6_df: pd.DataFrame) -> str:
    rows = [
        " & ".join([latex_escape(row["Статья"]), latex_escape(row["Сумма"])]) + r" \\ \hline"
        for _, row in table_6_df.iterrows()
    ]
    if not rows:
        rows = [r"\multicolumn{2}{|c|}{Нет данных} \\ \hline"]

    return wrap_longtable(
        [
            "",
            r"\begin{longtable}{|c|c|}",
            r"\caption{Итоговая смета}\label{tab:tab7} \\",
            r"\hline",
            r"Статья & Сумма \\ \hline",
            r"\endfirsthead",
            "",
            r"\caption*{Продолжение таблицы \ref{tab:tab7}}\\ \hline",
            r"Статья & Сумма \\ \hline",
            r"\endhead",
            "",
            r"\hline",
            r"\endfoot",
            "",
            r"\hline",
            r"\endlastfoot",
            "",
            *rows,
            "",
            r"\end{longtable}",
        ]
    )


def generate_all_latex_tables(
    table_1_df: pd.DataFrame,
    table_2_df: pd.DataFrame,
    table_3_df: pd.DataFrame,
    table_4_df: pd.DataFrame,
    table_5_df: pd.DataFrame,
    table_6_df: pd.DataFrame,
) -> str:
    return "\n\n".join(
        [
            r"% Requires: \usepackage{longtable}",
            r"% Requires: \usepackage{multirow}",
            r"% Requires: \usepackage{hhline}",
            "",
            build_table_1_latex(table_1_df),
            build_table_2_latex(table_2_df),
            build_table_3_latex(table_3_df),
            build_table_4_latex(table_4_df),
            build_table_5_latex(table_5_df),
            build_table_6_latex(table_6_df),
        ]
    )


def main() -> None:
    init_state()

    st.title("Расчет экономической части дипломного проекта")
    st.write("Вводите работы, оклады и оборудование, а приложение сразу пересчитает таблицы и подготовит LaTeX.")

    input_tab, preview_tab, export_tab = st.tabs(["Ввод данных", "Просмотр DataFrame", "Экспорт LaTeX"])

    with input_tab:
        st.subheader("Работы проекта")
        st.caption("Исполнители редактируются прямо в этой таблице. Оклады ниже синхронизируются автоматически.")
        works_input_df = st.data_editor(
            st.session_state.works_seed,
            key="works_editor",
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            column_config={
                "№ этапа": st.column_config.NumberColumn("№ этапа", min_value=1, step=1, format="%d"),
                "Название работы": st.column_config.TextColumn("Название работы"),
                "T_min": st.column_config.NumberColumn("T_min", min_value=0, step=1, format="%d"),
                "T_max": st.column_config.NumberColumn("T_max", min_value=0, step=1, format="%d"),
                "Исполнитель": st.column_config.TextColumn("Исполнитель"),
            },
        )

        works_df = calculate_works(works_input_df)
        workers = [worker for worker in works_df["Исполнитель"].drop_duplicates().tolist() if worker]

        st.subheader("Оклады исполнителей")
        salary_input_df = build_salary_editor_df(workers, st.session_state.salary_store)
        salary_editor_df = st.data_editor(
            salary_input_df,
            key="salary_editor",
            num_rows="fixed",
            width="stretch",
            hide_index=True,
            column_config={
                "Исполнитель": st.column_config.TextColumn("Исполнитель", disabled=True),
                "Оклад": st.column_config.NumberColumn("Оклад", min_value=0.0, step=1000.0, format="%.2f"),
            },
        )
        update_salary_store(salary_editor_df)

        st.subheader("Оборудование")
        equipment_input_df = st.data_editor(
            st.session_state.equipment_seed,
            key="equipment_editor",
            num_rows="dynamic",
            width="stretch",
            hide_index=True,
            column_config={
                "Название": st.column_config.TextColumn("Название"),
                "Кол-во": st.column_config.NumberColumn("Кол-во", min_value=0, step=1, format="%d"),
                "Цена": st.column_config.NumberColumn("Цена", min_value=0.0, step=100.0, format="%.2f"),
                "Срок амортизации в днях": st.column_config.NumberColumn(
                    "Срок амортизации в днях",
                    min_value=1,
                    step=1,
                    format="%d",
                ),
            },
        )

    works_df = calculate_works(works_input_df)
    equipment_df = normalize_equipment_df(equipment_input_df)
    table_1_df = build_table_1_df(works_df)
    table_2_df = build_table_2_df(works_df)
    table_3_df = build_table_3_df(table_2_df)
    table_4_df = build_table_4_df(works_df, salary_editor_df)
    total_project_days = round(to_float(works_df["T_d"].sum()) if not works_df.empty else 0.0, 2)
    table_5_df = build_table_5_df(equipment_df, total_project_days)
    table_6_df = build_table_6_df(table_4_df, table_5_df)
    latex_str = generate_all_latex_tables(table_1_df, table_2_df, table_3_df, table_4_df, table_5_df, table_6_df)

    with preview_tab:
        st.subheader("Расчетные таблицы")
        st.write(f"Общее время проекта: **{format_number(total_project_days)} чел/дней**")

        preview_tables = [
            ("Таблица 1. Оценка трудоемкости работ проекта", table_1_df),
            ("Таблица 2. Основные работы и события проекта", table_2_df),
            ("Таблица 3. Параметры сетевой модели", table_3_df),
            ("Таблица 4. Расчет заработной платы", table_4_df),
            ("Таблица 5. Затраты на оборудование", table_5_df),
            ("Таблица 6. Итоговая смета", table_6_df),
        ]
        for title, frame in preview_tables:
            st.markdown(f"### {title}")
            st.dataframe(dataframe_for_display(frame), width="stretch", hide_index=True)

    with export_tab:
        st.subheader("Экспорт LaTeX")
        if st.button("Сгенерировать LaTeX", type="primary"):
            st.session_state.latex_output = latex_str
        if st.session_state.latex_output:
            st.code(st.session_state.latex_output, language="latex")
        else:
            st.info("Нажмите кнопку, чтобы вывести код всех шести LaTeX-таблиц.")


if __name__ == "__main__":
    main()
