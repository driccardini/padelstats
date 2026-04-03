from __future__ import annotations

import os
from typing import Dict
from uuid import uuid4

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

try:
    import toml
except Exception:  # pragma: no cover - optional fallback parser
    toml = None

try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:  # pragma: no cover - optional dependency for local run before install
    gspread = None
    Credentials = None


STAT_KEYS = ["winner", "errores_no_forzados", "smash", "smash_winner"]
STAT_LABELS = {
    "winner": "Winner",
    "errores_no_forzados": "Errores no forzados",
    "smash": "Smash",
    "smash_winner": "Smash winner",
}

STAT_ICONS = {
    "winner": "🎯",
    "errores_no_forzados": "⚠️",
    "smash": "💥",
    "smash_winner": "🔥",
}

DEFAULT_GOOGLE_SHEET_ID = "1tcyldrxv5lZl2CKaK4-1Me73IasGlLWTVK7cuup9HRY"


def inject_court_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #2c8a57;
                background-image:
                    linear-gradient(#3aa56a, #2c8a57);
                background-size: 100% 100%;
            }

            .block-container {
                padding-top: 1.2rem;
            }

            .court-title {
                text-align: center;
                color: #f7fff9;
                font-weight: 700;
                font-size: 1.2rem;
                letter-spacing: 0.02em;
                margin-bottom: 0.2rem;
            }

            .court-subtitle {
                text-align: center;
                color: #d8f2e3;
                margin-bottom: 1rem;
            }

            .quadrant-shell {
                background: rgba(21, 92, 58, 0.62);
                border: 2px solid rgba(255, 255, 255, 0.9);
                border-radius: 14px;
                padding: 10px;
                margin-bottom: 10px;
                box-shadow: 0 6px 22px rgba(0, 0, 0, 0.18);
            }

            .court-board {
                border: 3px solid rgba(255, 255, 255, 0.95);
                border-radius: 18px;
                padding: 12px;
                background: rgba(25, 110, 68, 0.35);
            }

            .court-midline {
                height: 4px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.95);
                margin: 6px 6px 12px 6px;
            }

            .player-name {
                text-align: center;
                color: #ffffff;
                font-size: 1.2rem;
                font-weight: 700;
                margin-bottom: 0.25rem;
            }

            .set-label {
                text-align: center;
                color: #d9f6e6;
                font-weight: 600;
                margin-bottom: 0.35rem;
            }

            .saved-set-wrap {
                margin-top: 12px;
                margin-bottom: 10px;
                border: 2px solid rgba(255, 255, 255, 0.85);
                border-radius: 14px;
                background: rgba(12, 69, 42, 0.58);
                padding: 10px;
            }

            .saved-set-title {
                color: #ffffff;
                text-align: center;
                font-size: 1rem;
                font-weight: 700;
                margin-bottom: 8px;
            }

            .saved-card {
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.08);
                padding: 8px;
                margin-bottom: 8px;
            }

            .saved-player {
                color: #ffffff;
                text-align: center;
                font-weight: 700;
                margin-bottom: 6px;
            }

            .saved-row {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                color: #eafff2;
                font-size: 0.9rem;
                margin-bottom: 4px;
            }

            .summary-wrap {
                margin-top: 10px;
                border: 2px solid rgba(255, 255, 255, 0.85);
                border-radius: 14px;
                background: rgba(12, 69, 42, 0.58);
                padding: 10px;
            }

            .summary-title {
                color: #ffffff;
                text-align: center;
                font-size: 1rem;
                font-weight: 700;
                margin-bottom: 8px;
            }

            .summary-card {
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.08);
                padding: 10px;
                margin-bottom: 8px;
            }

            .summary-player {
                color: #ffffff;
                text-align: center;
                font-weight: 700;
                margin-bottom: 8px;
                font-size: 1rem;
            }

            .summary-subtitle {
                color: #d9f6e6;
                font-size: 0.8rem;
                font-weight: 700;
                margin-top: 6px;
                margin-bottom: 4px;
                text-transform: uppercase;
                letter-spacing: 0.03em;
            }

            .summary-row {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                color: #eafff2;
                font-size: 0.88rem;
                margin-bottom: 4px;
            }

            .match-toolbar {
                margin-bottom: 12px;
                border: 2px solid rgba(255, 255, 255, 0.85);
                border-radius: 14px;
                background: rgba(12, 69, 42, 0.58);
                padding: 10px;
            }

            .match-meta {
                color: #ffffff;
                text-align: center;
                font-weight: 700;
                margin-bottom: 8px;
            }

            [data-testid="stMetric"] {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.45);
                border-radius: 10px;
                padding: 8px 4px;
            }

            .stat-bubble {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 10px;
                padding: 8px 6px;
                min-height: 70px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
            }

            .stat-label {
                color: #e8fff1;
                font-size: 0.82rem;
                line-height: 1.1;
                margin-bottom: 2px;
            }

            .stat-value {
                color: #ffffff;
                font-size: 1.35rem;
                font-weight: 700;
                line-height: 1;
            }

            [data-testid="stMetricLabel"],
            [data-testid="stMetricValue"] {
                text-align: center;
                justify-content: center;
                color: #ffffff;
            }

            [data-testid="stButton"] > button {
                font-size: 1.35rem;
                font-weight: 700;
                border-radius: 10px;
                border: 2px solid #111111;
                background: #f5f5f5;
                color: #000000;
                min-height: 44px;
            }

            [data-testid="stButton"] > button[data-testid^="baseButton-secondary"][kind="secondary"] {
                letter-spacing: 0.02em;
            }

            [data-testid="stButton"] > button p {
                color: #000000;
                font-weight: 800;
                font-size: 1.45rem;
                font-family: "Arial", "Helvetica", sans-serif;
            }

            @media (max-width: 900px) {
                .player-name {
                    font-size: 1.05rem;
                }

                [data-testid="stButton"] > button {
                    min-height: 48px;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ensure_state() -> None:
    if "screen" not in st.session_state:
        st.session_state.screen = "setup"

    if "match_id" not in st.session_state:
        st.session_state.match_id = f"M-{uuid4().hex[:8].upper()}"

    if "match_name" not in st.session_state:
        st.session_state.match_name = "Equipo A vs Equipo B"

    if "player_names" not in st.session_state:
        st.session_state.player_names = {
            "q1": "Jugador 1",
            "q2": "Jugador 2",
            "q3": "Jugador 3",
            "q4": "Jugador 4",
        }

    if "selected_set" not in st.session_state:
        st.session_state.selected_set = 1

    if "last_saved_set" not in st.session_state:
        st.session_state.last_saved_set = None

    if "active_quadrant" not in st.session_state:
        st.session_state.active_quadrant = "q1"

    if "match_view" not in st.session_state:
        st.session_state.match_view = "Mobile"

    if "stats" not in st.session_state:
        st.session_state.stats = {
            set_number: {
                quadrant: {stat: 0 for stat in STAT_KEYS}
                for quadrant in ["q1", "q2", "q3", "q4"]
            }
            for set_number in [1, 2, 3]
        }

    # Campos para pantalla inicial.
    if "setup_match_name" not in st.session_state:
        st.session_state.setup_match_name = ""
    if "setup_player_q1" not in st.session_state:
        st.session_state.setup_player_q1 = ""
    if "setup_player_q2" not in st.session_state:
        st.session_state.setup_player_q2 = ""
    if "setup_player_q3" not in st.session_state:
        st.session_state.setup_player_q3 = ""
    if "setup_player_q4" not in st.session_state:
        st.session_state.setup_player_q4 = ""


def inc_stat(quadrant: str, stat_key: str) -> None:
    current_set = st.session_state.selected_set
    st.session_state.stats[current_set][quadrant][stat_key] += 1


def dec_stat(quadrant: str, stat_key: str) -> None:
    current_set = st.session_state.selected_set
    st.session_state.stats[current_set][quadrant][stat_key] = max(
        0,
        st.session_state.stats[current_set][quadrant][stat_key] - 1,
    )


def reset_set_stats(set_number: int) -> None:
    for quadrant in ["q1", "q2", "q3", "q4"]:
        for stat in STAT_KEYS:
            st.session_state.stats[set_number][quadrant][stat] = 0


def reset_match_stats() -> None:
    for set_number in [1, 2, 3]:
        reset_set_stats(set_number)


def to_sheet_row_for_set(set_number: int) -> list:
    q1 = st.session_state.stats[set_number]["q1"]
    q2 = st.session_state.stats[set_number]["q2"]
    q3 = st.session_state.stats[set_number]["q3"]
    q4 = st.session_state.stats[set_number]["q4"]

    return [
        st.session_state.match_name,
        f"SET {set_number}",
        st.session_state.player_names["q1"],
        st.session_state.player_names["q2"],
        st.session_state.player_names["q3"],
        st.session_state.player_names["q4"],
        q1["winner"],
        q1["errores_no_forzados"],
        q1["smash"],
        q1["smash_winner"],
        q2["winner"],
        q2["errores_no_forzados"],
        q2["smash"],
        q2["smash_winner"],
        q3["winner"],
        q3["errores_no_forzados"],
        q3["smash"],
        q3["smash_winner"],
        q4["winner"],
        q4["errores_no_forzados"],
        q4["smash"],
        q4["smash_winner"],
    ]


def get_player_totals(quadrant: str) -> Dict[str, int]:
    totals = {key: 0 for key in STAT_KEYS}
    for set_number in [1, 2, 3]:
        for stat in STAT_KEYS:
            totals[stat] += st.session_state.stats[set_number][quadrant][stat]
    return totals


def get_global_summary_rows() -> list[Dict[str, int | str]]:
    rows = []
    for quadrant in ["q1", "q2", "q3", "q4"]:
        totals = get_player_totals(quadrant)
        rows.append(
            {
                "Jugador": st.session_state.player_names[quadrant],
                "Winners": totals["winner"],
                "Errores no forzados": totals["errores_no_forzados"],
                "Smash": totals["smash"],
                "Smash winners": totals["smash_winner"],
            }
        )
    return rows


def get_set_summary_rows() -> list[Dict[str, int | str]]:
    rows = []
    for set_number in [1, 2, 3]:
        for quadrant in ["q1", "q2", "q3", "q4"]:
            stats = st.session_state.stats[set_number][quadrant]
            rows.append(
                {
                    "Set": f"SET {set_number}",
                    "Jugador": st.session_state.player_names[quadrant],
                    "Winners": stats["winner"],
                    "Errores no forzados": stats["errores_no_forzados"],
                    "Smash": stats["smash"],
                    "Smash winners": stats["smash_winner"],
                }
            )
    return rows


def get_service_account_info() -> Dict | None:
    required_keys = {
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "token_uri",
    }

    try:
        info = dict(st.secrets["gcp_service_account"])
    except (StreamlitSecretNotFoundError, KeyError):
        return None

    if not required_keys.issubset(set(info.keys())):
        return None

    private_key = str(info.get("private_key", "")).strip()
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")
    info["private_key"] = private_key

    return info


def validate_service_account_info(info: Dict) -> tuple[bool, str]:
    placeholder_tokens = [
        "TU_PROJECT_ID",
        "TU_PRIVATE_KEY_ID",
        "TU_CLAVE_PRIVADA",
        "TU_CLIENT_EMAIL",
        "TU_CLIENT_ID",
    ]
    blob = "\n".join(str(v) for v in info.values())
    if any(token in blob for token in placeholder_tokens):
        return False, "El archivo secrets.toml todavía tiene valores de ejemplo (TU_...)."

    private_key = str(info.get("private_key", ""))
    if "BEGIN PRIVATE KEY" not in private_key or "END PRIVATE KEY" not in private_key:
        return False, "private_key no tiene formato PEM válido."

    return True, "ok"


def resolve_google_sheet_id() -> str | None:
    # 1) Streamlit secrets
    try:
        value = st.secrets["google_sheet_id"]
        if str(value).strip():
            return str(value).strip()
    except (StreamlitSecretNotFoundError, KeyError):
        pass

    # 2) Environment variable fallback
    env_value = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if env_value:
        return env_value

    # 3) Direct parse of local/user secrets.toml
    if toml is not None:
        candidate_paths = [
            os.path.join(os.getcwd(), ".streamlit", "secrets.toml"),
            os.path.join(os.path.expanduser("~"), ".streamlit", "secrets.toml"),
        ]
        for path in candidate_paths:
            if not os.path.exists(path):
                continue
            try:
                parsed = toml.load(path)
                parsed_value = str(parsed.get("google_sheet_id", "")).strip()
                if parsed_value:
                    return parsed_value
            except Exception:
                continue

    # 4) Project default fallback for this app.
    return DEFAULT_GOOGLE_SHEET_ID


def save_set_to_google_sheet(set_number: int) -> tuple[bool, str]:
    if gspread is None or Credentials is None:
        return False, "Faltan dependencias. Instalá primero con: uv sync"

    sheet_id = resolve_google_sheet_id()
    if not sheet_id:
        return (False, "No se pudo resolver google_sheet_id")

    service_account_info = get_service_account_info()
    if not service_account_info:
        return (
            False,
            "Falta gcp_service_account en .streamlit/secrets.toml",
        )

    valid, validation_message = validate_service_account_info(service_account_info)
    if not valid:
        return False, validation_message

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scope)
        client = gspread.authorize(credentials)

        spreadsheet = client.open_by_key(sheet_id)
        try:
            worksheet_name = st.secrets["google_worksheet"]
        except (StreamlitSecretNotFoundError, KeyError):
            worksheet_name = None
        used_fallback_sheet = False
        if worksheet_name:
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.sheet1
                used_fallback_sheet = True
        else:
            worksheet = spreadsheet.sheet1

        row = to_sheet_row_for_set(set_number)
        worksheet.append_row(row, value_input_option="RAW")
    except Exception as exc:
        return False, f"Error guardando en Google Sheets: {exc}"

    if used_fallback_sheet:
        return (
            True,
            f"Set {set_number} guardado en Google Sheets (pestaña configurada no existe, se usó {worksheet.title})",
        )

    return True, f"Set {set_number} guardado en Google Sheets (1 fila)"


def start_match() -> tuple[bool, str]:
    names = {
        "q1": st.session_state.setup_player_q1.strip(),
        "q2": st.session_state.setup_player_q2.strip(),
        "q3": st.session_state.setup_player_q3.strip(),
        "q4": st.session_state.setup_player_q4.strip(),
    }
    if not all(names.values()):
        return False, "Completá el nombre de los 4 jugadores"

    match_name = st.session_state.setup_match_name.strip()
    if not match_name:
        return False, "Completá el nombre del partido"

    st.session_state.player_names = names
    st.session_state.match_name = match_name
    st.session_state.screen = "match"
    return True, "Partido iniciado"


def finish_match() -> None:
    st.session_state.screen = "summary"


def start_new_match() -> None:
    st.session_state.match_id = f"M-{uuid4().hex[:8].upper()}"
    st.session_state.match_name = "Equipo A vs Equipo B"
    st.session_state.setup_match_name = ""
    st.session_state.player_names = {
        "q1": "Jugador 1",
        "q2": "Jugador 2",
        "q3": "Jugador 3",
        "q4": "Jugador 4",
    }
    st.session_state.setup_player_q1 = ""
    st.session_state.setup_player_q2 = ""
    st.session_state.setup_player_q3 = ""
    st.session_state.setup_player_q4 = ""
    st.session_state.selected_set = 1
    reset_match_stats()
    st.session_state.screen = "setup"


def render_quadrant(quadrant: str) -> None:
    set_number = st.session_state.selected_set
    player_name = st.session_state.player_names[quadrant]
    player_stats = st.session_state.stats[set_number][quadrant]

    st.markdown('<div class="quadrant-shell">', unsafe_allow_html=True)
    st.markdown(f'<div class="player-name">{player_name}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="set-label">SET {set_number}</div>', unsafe_allow_html=True)

    for stat in STAT_KEYS:
        label = STAT_LABELS[stat]
        value = player_stats[stat]
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.button(
                "−",
                key=f"dec_{quadrant}_{stat}_{set_number}",
                on_click=dec_stat,
                args=(quadrant, stat),
                use_container_width=True,
            )
        with c2:
            st.markdown(
                (
                    '<div class="stat-bubble">'
                    f'<div class="stat-label">{label}</div>'
                    f'<div class="stat-value">{value}</div>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        with c3:
            st.button(
                "＋",
                key=f"inc_{quadrant}_{stat}_{set_number}",
                on_click=inc_stat,
                args=(quadrant, stat),
                use_container_width=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def render_saved_set_summary(set_number: int) -> None:
    st.markdown('<div class="saved-set-wrap">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="saved-set-title">Resumen visual de SET {set_number} guardado</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    columns = [c1, c2, c3, c4]
    quadrants = ["q1", "q2", "q3", "q4"]
    for col, quadrant in zip(columns, quadrants):
        with col:
            player_name = st.session_state.player_names[quadrant]
            stats = st.session_state.stats[set_number][quadrant]
            st.markdown('<div class="saved-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="saved-player">{player_name}</div>', unsafe_allow_html=True)
            for stat in STAT_KEYS:
                st.markdown(
                    (
                        '<div class="saved-row">'
                        f'<span>{STAT_ICONS[stat]} {STAT_LABELS[stat]}</span>'
                        f'<strong>{stats[stat]}</strong>'
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_mobile_player_selector() -> None:
    st.markdown('<div class="summary-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="summary-title">Jugador activo</div>', unsafe_allow_html=True)

    q1, q2 = st.columns(2)
    with q1:
        if st.button(
            st.session_state.player_names["q1"],
            key="active_q1",
            type="primary" if st.session_state.active_quadrant == "q1" else "secondary",
            use_container_width=True,
        ):
            st.session_state.active_quadrant = "q1"
            st.rerun()
    with q2:
        if st.button(
            st.session_state.player_names["q2"],
            key="active_q2",
            type="primary" if st.session_state.active_quadrant == "q2" else "secondary",
            use_container_width=True,
        ):
            st.session_state.active_quadrant = "q2"
            st.rerun()

    q3, q4 = st.columns(2)
    with q3:
        if st.button(
            st.session_state.player_names["q3"],
            key="active_q3",
            type="primary" if st.session_state.active_quadrant == "q3" else "secondary",
            use_container_width=True,
        ):
            st.session_state.active_quadrant = "q3"
            st.rerun()
    with q4:
        if st.button(
            st.session_state.player_names["q4"],
            key="active_q4",
            type="primary" if st.session_state.active_quadrant == "q4" else "secondary",
            use_container_width=True,
        ):
            st.session_state.active_quadrant = "q4"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_match_toolbar() -> None:
    st.markdown('<div class="match-toolbar">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="match-meta">{st.session_state.match_name} | ID: {st.session_state.match_id}</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Set activo", options=[1, 2, 3], key="selected_set")
    with c2:
        st.radio("Vista", options=["Mobile", "Cancha"], key="match_view", horizontal=True)

    c3, c4 = st.columns(2)
    with c3:
        if st.button("Reset set actual", use_container_width=True):
            reset_set_stats(st.session_state.selected_set)
            st.success("Set reseteado")
    with c4:
        if st.button("Guardar set en Google Sheets", type="primary", use_container_width=True):
            ok, msg = save_set_to_google_sheet(st.session_state.selected_set)
            if ok:
                st.session_state.last_saved_set = st.session_state.selected_set
                st.success(msg)
            else:
                st.error(msg)

    c5, c6 = st.columns(2)
    with c5:
        if st.button("Reset partido completo", use_container_width=True):
            reset_match_stats()
            st.success("Partido reseteado")
    with c6:
        if st.button("Finalizar partido", use_container_width=True):
            finish_match()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_court_view() -> None:
    st.markdown('<div class="court-board">', unsafe_allow_html=True)

    top_left, top_right = st.columns(2)
    with top_left:
        render_quadrant("q1")
    with top_right:
        render_quadrant("q2")

    st.markdown('<div class="court-midline"></div>', unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        render_quadrant("q3")
    with bottom_right:
        render_quadrant("q4")

    st.markdown("</div>", unsafe_allow_html=True)


def render_mobile_view() -> None:
    render_mobile_player_selector()
    render_quadrant(st.session_state.active_quadrant)


def render_player_summary_card(quadrant: str) -> None:
    player_name = st.session_state.player_names[quadrant]
    global_stats = get_player_totals(quadrant)

    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-player">{player_name}</div>', unsafe_allow_html=True)

    st.markdown('<div class="summary-subtitle">Por set</div>', unsafe_allow_html=True)
    for set_number in [1, 2, 3]:
        set_stats = st.session_state.stats[set_number][quadrant]
        st.markdown(
            (
                '<div class="summary-row">'
                f'<span>SET {set_number}</span>'
                f'<span>{STAT_ICONS["winner"]} {set_stats["winner"]} | '
                f'{STAT_ICONS["errores_no_forzados"]} {set_stats["errores_no_forzados"]} | '
                f'{STAT_ICONS["smash"]} {set_stats["smash"]} | '
                f'{STAT_ICONS["smash_winner"]} {set_stats["smash_winner"]}</span>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<div class="summary-subtitle">Global</div>', unsafe_allow_html=True)
    st.markdown(
        (
            '<div class="summary-row">'
            f'<span>{STAT_ICONS["winner"]} Winners</span><strong>{global_stats["winner"]}</strong>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="summary-row">'
            f'<span>{STAT_ICONS["errores_no_forzados"]} Errores no forzados</span>'
            f'<strong>{global_stats["errores_no_forzados"]}</strong>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="summary-row">'
            f'<span>{STAT_ICONS["smash"]} Smash</span><strong>{global_stats["smash"]}</strong>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="summary-row">'
            f'<span>{STAT_ICONS["smash_winner"]} Smash winner</span>'
            f'<strong>{global_stats["smash_winner"]}</strong>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


def render_setup_screen() -> None:
    st.title("Padel Match Setup")
    st.caption("Pantalla previa para cargar nombres antes de iniciar el partido")

    with st.form("setup_form"):
        st.text_input("Nombre del partido", key="setup_match_name", placeholder="Equipo A vs Equipo B")
        st.text_input("Jugador cuadrante superior izquierdo", key="setup_player_q1", placeholder="Jugador 1")
        st.text_input("Jugador cuadrante superior derecho", key="setup_player_q2", placeholder="Jugador 2")
        st.text_input("Jugador cuadrante inferior izquierdo", key="setup_player_q3", placeholder="Jugador 3")
        st.text_input("Jugador cuadrante inferior derecho", key="setup_player_q4", placeholder="Jugador 4")

        submitted = st.form_submit_button("Iniciar partido", type="primary")
        if submitted:
            ok, msg = start_match()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def render_match_screen() -> None:
    inject_court_styles()
    st.markdown('<div class="court-title">Padel Match Stats</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="court-subtitle">Estadísticas por set (partido al mejor de 3)</div>',
        unsafe_allow_html=True,
    )

    render_match_toolbar()

    if st.session_state.match_view == "Mobile":
        render_mobile_view()
    else:
        render_court_view()

    if st.session_state.last_saved_set:
        render_saved_set_summary(st.session_state.last_saved_set)


def render_summary_screen() -> None:
    inject_court_styles()
    st.title("Resumen de partido")
    st.caption(f"{st.session_state.match_name} | ID: {st.session_state.match_id}")

    st.markdown('<div class="summary-wrap">', unsafe_allow_html=True)
    st.markdown(
        '<div class="summary-title">Jugador + Sets + Métricas + Global</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        render_player_summary_card("q1")
    with c2:
        render_player_summary_card("q2")

    c3, c4 = st.columns(2)
    with c3:
        render_player_summary_card("q3")
    with c4:
        render_player_summary_card("q4")

    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Volver al partido", use_container_width=True):
            st.session_state.screen = "match"
            st.rerun()
    with c2:
        if st.button("Nuevo partido", type="primary", use_container_width=True):
            start_new_match()
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Padel Stats", page_icon="🎾", layout="wide")
    ensure_state()

    if st.session_state.screen == "setup":
        render_setup_screen()
    elif st.session_state.screen == "match":
        render_match_screen()
    else:
        render_summary_screen()


if __name__ == "__main__":
    main()
