from __future__ import annotations

import os
import json
import time
from pathlib import Path
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


def get_candidate_secret_paths() -> list[str]:
    project_root = Path(__file__).resolve().parent
    return [
        str(project_root / ".streamlit" / "secrets.toml"),
        str(Path.cwd() / ".streamlit" / "secrets.toml"),
        str(Path.home() / ".streamlit" / "secrets.toml"),
    ]


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
        st.session_state.screen = "home"

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

    if "autosave_signatures" not in st.session_state:
        st.session_state.autosave_signatures = {}

    if "autosave_last_tick" not in st.session_state:
        st.session_state.autosave_last_tick = 0.0

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

    if "current_tab" not in st.session_state:
        st.session_state.current_tab = "Nuevo Partido"


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

    info = None

    # 1) Streamlit secrets
    try:
        info = dict(st.secrets["gcp_service_account"])
    except (StreamlitSecretNotFoundError, KeyError):
        info = None

    # 2) Environment variable fallback with JSON blob
    if info is None:
        raw_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "").strip()
        if raw_json:
            try:
                info = json.loads(raw_json)
            except Exception:
                info = None

    # 3) Direct parse of local/user secrets.toml
    if info is None and toml is not None:
        for path in get_candidate_secret_paths():
            if not os.path.exists(path):
                continue
            try:
                parsed = toml.load(path)
                section = parsed.get("gcp_service_account")
                if isinstance(section, dict):
                    info = dict(section)
                    break
            except Exception:
                continue

    if info is None:
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
        for path in get_candidate_secret_paths():
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
        checked_paths = ", ".join(get_candidate_secret_paths())
        return (
            False,
            f"Falta gcp_service_account. Rutas buscadas: {checked_paths}",
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

        # Upsert por Partido + Set: actualiza la fila existente si ya está.
        all_values = worksheet.get_all_values()
        target_match = str(st.session_state.match_name).strip()
        target_set = f"SET {set_number}"
        target_row_index = None

        for idx, existing in enumerate(all_values, start=1):
            if len(existing) < 2:
                continue
            col_match = str(existing[0]).strip()
            col_set = str(existing[1]).strip()

            # Salta encabezado típico.
            if idx == 1 and col_match.lower() == "partido" and col_set.lower() == "set":
                continue

            if col_match == target_match and col_set == target_set:
                target_row_index = idx
                break

        if target_row_index is not None:
            worksheet.update(
                f"A{target_row_index}:V{target_row_index}",
                [row],
                value_input_option="RAW",
            )
        else:
            worksheet.append_row(row, value_input_option="RAW")
    except Exception as exc:
        return False, f"Error guardando en Google Sheets: {exc}"

    if used_fallback_sheet:
        return (
            True,
            f"Set {set_number} guardado en Google Sheets (pestaña configurada no existe, se usó {worksheet.title})",
        )

    if target_row_index is not None:
        return True, f"Set {set_number} actualizado en Google Sheets (fila {target_row_index})"

    return True, f"Set {set_number} guardado en Google Sheets (nueva fila)"


def build_set_signature(set_number: int) -> tuple:
    values = []
    for quadrant in ["q1", "q2", "q3", "q4"]:
        values.append(st.session_state.player_names[quadrant])
        for stat in STAT_KEYS:
            values.append(st.session_state.stats[set_number][quadrant][stat])
    return (st.session_state.match_name, set_number, *values)


def run_silent_autosave() -> None:
    # No muestra mensajes en UI. Guarda solo si cambió el set activo.
    set_number = st.session_state.selected_set
    signature = build_set_signature(set_number)
    saved_signature = st.session_state.autosave_signatures.get(set_number)
    if signature == saved_signature:
        return

    ok, _ = save_set_to_google_sheet(set_number)
    if ok:
        st.session_state.autosave_signatures[set_number] = signature
    st.session_state.autosave_last_tick = time.time()


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
        if st.button("Guardar set en Google Sheets", use_container_width=True):
            ok, msg = save_set_to_google_sheet(st.session_state.selected_set)
            if ok:
                st.session_state.last_saved_set = st.session_state.selected_set
                st.session_state.autosave_signatures[st.session_state.selected_set] = build_set_signature(
                    st.session_state.selected_set
                )
                st.success(msg)
            else:
                st.warning(msg)

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

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Iniciar partido", type="primary", use_container_width=True)
            if submitted:
                ok, msg = start_match()
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        with col2:
            if st.form_submit_button("Cancelar", use_container_width=True):
                st.session_state.screen = "home"
                st.rerun()


def render_match_screen() -> None:
    inject_court_styles()
    st.markdown('<div class="court-title">Padel Match Stats</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="court-subtitle">Estadísticas por set (partido al mejor de 3)</div>',
        unsafe_allow_html=True,
    )

    render_match_toolbar()

    if hasattr(st, "fragment"):

        @st.fragment(run_every="10s")
        def autosave_fragment() -> None:
            if st.session_state.screen == "match":
                run_silent_autosave()

        autosave_fragment()

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

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Volver al partido", use_container_width=True):
            st.session_state.screen = "match"
            st.rerun()
    with c2:
        if st.button("Nuevo partido", type="primary", use_container_width=True):
            start_new_match()
            st.rerun()
    with c3:
        if st.button("🏠 Inicio", use_container_width=True):
            st.session_state.screen = "home"
            st.rerun()


def fetch_all_matches_from_sheet() -> list[dict] | None:
    """Trae todos los partidos guardados en Google Sheets."""
    if gspread is None or Credentials is None:
        return None

    sheet_id = resolve_google_sheet_id()
    if not sheet_id:
        return None

    service_account_info = get_service_account_info()
    if not service_account_info:
        return None

    valid, _ = validate_service_account_info(service_account_info)
    if not valid:
        return None

    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scope)
        client = gspread.authorize(credentials)

        spreadsheet = client.open_by_key(sheet_id)
        try:
            worksheet_name = st.secrets["google_worksheet"]
        except (StreamlitSecretNotFoundError, KeyError):
            worksheet_name = None

        if worksheet_name:
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.sheet1
        else:
            worksheet = spreadsheet.sheet1

        all_values = worksheet.get_all_values()
        if not all_values:
            return []

        # Estructura esperada basada en to_sheet_row_for_set
        # [Partido, Set, j1, j2, j3, j4, q1_winner, q1_error, q1_smash, q1_smash_w, q2_winner, ...]
        matches_dict = {}

        for row_idx, row in enumerate(all_values):
            if row_idx == 0:  # Skip header
                continue
            if len(row) < 6:
                continue

            match_name = row[0].strip()
            set_label = row[1].strip()

            if match_name not in matches_dict:
                matches_dict[match_name] = {
                    "name": match_name,
                    "sets": {},
                    "players": [row[2].strip(), row[3].strip(), row[4].strip(), row[5].strip()],
                    "row_index": row_idx,
                }

            # Parsear estadísticas por jugador para este set
            set_data = {
                "set_label": set_label,
                "players": [row[2].strip(), row[3].strip(), row[4].strip(), row[5].strip()],
                "stats": {},
                "row_index": row_idx,
            }

            # q1 = columnas 6-9, q2 = 10-13, q3 = 14-17, q4 = 18-21
            quadrants = ["q1", "q2", "q3", "q4"]
            stat_indices = [
                [6, 7, 8, 9],
                [10, 11, 12, 13],
                [14, 15, 16, 17],
                [18, 19, 20, 21],
            ]

            for q_idx, (quad, indices) in enumerate(zip(quadrants, stat_indices)):
                set_data["stats"][quad] = {
                    "winner": int(row[indices[0]]) if indices[0] < len(row) and row[indices[0]].isdigit() else 0,
                    "errores_no_forzados": int(row[indices[1]]) if indices[1] < len(row) and row[indices[1]].isdigit() else 0,
                    "smash": int(row[indices[2]]) if indices[2] < len(row) and row[indices[2]].isdigit() else 0,
                    "smash_winner": int(row[indices[3]]) if indices[3] < len(row) and row[indices[3]].isdigit() else 0,
                }

            matches_dict[match_name]["sets"][set_label] = set_data

        return list(matches_dict.values())

    except Exception:
        return None


def calculate_player_performance(match: dict) -> dict:
    """Calcula puntuación de rendimiento por jugador para el MVP."""
    player_scores = {}
    for player in match["players"]:
        player_scores[player] = 0

    # Sumar estadísticas de todos los sets
    for set_label, set_data in match["sets"].items():
        for q_idx, quadrant in enumerate(["q1", "q2", "q3", "q4"]):
            player = set_data["players"][q_idx]
            stats = set_data["stats"][quadrant]
            
            # Scoring: Winners +3, Smash Winners +2, Smash +1, Errors -1
            score = (stats["winner"] * 3 + 
                    stats["smash_winner"] * 2 + 
                    stats["smash"] * 1 - 
                    stats["errores_no_forzados"] * 1)
            player_scores[player] += score

    return player_scores


def render_history_screen() -> None:
    """Pantalla de histórico de partidos con opción de ver MVP."""
    inject_court_styles()
    st.markdown('<div class="court-title">📊 Histórico de Partidos</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="court-subtitle">Todas tus partidas y estadísticas en detalle</div>',
        unsafe_allow_html=True,
    )

    matches = fetch_all_matches_from_sheet()

    if matches is None:
        st.error("❌ No se pudieron cargar los partidos. Verifica tu conexión a Google Sheets.")
        return

    if not matches:
        st.info("📭 No hay partidos guardados aún. ¡Crea uno nuevo para comenzar!")
        if st.button("Crear nuevo partido", type="primary"):
            st.session_state.screen = "setup"
            st.rerun()
        return

    # Mostrar lista de partidos
    st.subheader(f"📈 Total de partidos: {len(matches)}")

    for match in reversed(matches):  # Mostrar más recientes primero
        player_scores = calculate_player_performance(match)
        best_player = max(player_scores, key=player_scores.get)
        
        with st.expander(f"🎾 {match['name']} | {len(match['sets'])} sets", expanded=False):
            # Encabezado del partido
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**👥 Jugadores:**")
                for player in match["players"]:
                    emoji = "⭐" if player == best_player else "  "
                    st.text(f"{emoji} {player}")

            with col2:
                st.markdown("**⚙️ Información:**")
                st.text(f"Sets: {len(match['sets'])}")
                st.text(f"Puntos totales: {sum(player_scores.values())}")

            with col3:
                st.markdown("**🏆 MVP Estimado:**")
                st.markdown(f"### {best_player}")
                st.text(f"Pts: {player_scores[best_player]}")

            st.divider()

            # Mostrar estadísticas por set
            for set_label, set_data in sorted(match["sets"].items()):
                st.markdown(f"### {set_label} 🎯")

                # Crear tabla de estadísticas con más iconos
                table_data = []
                for q_idx, quadrant in enumerate(["q1", "q2", "q3", "q4"]):
                    stats = set_data["stats"][quadrant]
                    player = set_data["players"][q_idx]
                    
                    # Calcular total de esta jugada en este set
                    total_score = (stats["winner"] * 3 + 
                                 stats["smash_winner"] * 2 + 
                                 stats["smash"] * 1)
                    
                    table_data.append({
                        "👤 Jugador": player,
                        "🎯 Winners": f"{stats['winner']} 🎯",
                        "⚠️ Errores": f"{stats['errores_no_forzados']} ⚠️",
                        "💥 Smash": f"{stats['smash']} 💥",
                        "🔥 Smash W": f"{stats['smash_winner']} 🔥",
                    })

                st.dataframe(table_data, use_container_width=True, hide_index=True)
                st.markdown("---")

            # Opción para seleccionar MVP del partido
            st.markdown("### 🏆 Designar MVP del Partido")
            col1, col2 = st.columns([3, 1])
            with col1:
                mvp_player = st.selectbox(
                    "Selecciona el MVP:",
                    options=match["players"] + ["Sin designar"],
                    key=f"mvp_{match['name']}",
                    index=match["players"].index(best_player) if best_player in match["players"] else len(match["players"]),
                )
            with col2:
                if st.button(
                    "💾 Guardar",
                    key=f"save_mvp_{match['name']}",
                    use_container_width=True,
                ):
                    if mvp_player == "Sin designar":
                        st.info("ℹ️ MVP no designado")
                    else:
                        st.success(f"✅ {mvp_player} es el MVP de {match['name']}")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Crear nuevo partido", type="primary", use_container_width=True):
            st.session_state.screen = "setup"
            st.rerun()

    with col2:
        if st.button("🏠 Volver al inicio", use_container_width=True):
            st.session_state.screen = "home"
            st.rerun()


def render_home_screen() -> None:
    """Pantalla de inicio principal con opciones para nuevo partido o histórico."""
    inject_court_styles()
    
    st.markdown('<div class="court-title">🎾 Padel Stats</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="court-subtitle">Gestor de estadísticas de partidos de pádel</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Mostrar dos opciones principais
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style="
                background: rgba(21, 92, 58, 0.62);
                border: 2px solid rgba(255, 255, 255, 0.9);
                border-radius: 14px;
                padding: 30px;
                text-align: center;
                box-shadow: 0 6px 22px rgba(0, 0, 0, 0.18);
            ">
                <div style="font-size: 3em;">➕</div>
                <div style="color: #f7fff9; font-weight: 700; font-size: 1.3em; margin: 15px 0;">
                    Nuevo Partido
                </div>
                <div style="color: #d8f2e3; font-size: 0.95em;">
                    Comienza a registrar estadísticas de un nuevo encuentro
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Iniciar", key="btn_new_match", use_container_width=True, type="primary"):
            st.session_state.screen = "setup"
            st.rerun()

    with col2:
        st.markdown(
            """
            <div style="
                background: rgba(21, 92, 58, 0.62);
                border: 2px solid rgba(255, 255, 255, 0.9);
                border-radius: 14px;
                padding: 30px;
                text-align: center;
                box-shadow: 0 6px 22px rgba(0, 0, 0, 0.18);
            ">
                <div style="font-size: 3em;">📊</div>
                <div style="color: #f7fff9; font-weight: 700; font-size: 1.3em; margin: 15px 0;">
                    Histórico
                </div>
                <div style="color: #d8f2e3; font-size: 0.95em;">
                    Visualiza todos tus partidos anteriores y estadísticas
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ver", key="btn_history", use_container_width=True, type="primary"):
            st.session_state.screen = "history"
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="Padel Stats", page_icon="🎾", layout="wide")
    ensure_state()

    if st.session_state.screen == "home":
        render_home_screen()
    elif st.session_state.screen == "setup":
        render_setup_screen()
    elif st.session_state.screen == "match":
        render_match_screen()
    elif st.session_state.screen == "history":
        render_history_screen()
    else:
        render_summary_screen()


if __name__ == "__main__":
    main()
