from __future__ import annotations

import os
import json
import hmac
import time
from datetime import datetime
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
PAIR_STAT_KEYS = ["posibilidades_quiebre", "quiebres"]
SET_TIME_HEADERS = ["Inicio set", "Fin set", "Duracion set"]
STAT_LABELS = {
    "winner": "Winner",
    "errores_no_forzados": "Errores no forzados",
    "smash": "Smash",
    "smash_winner": "Smash winner",
}
PAIR_STAT_LABELS = {
    "posibilidades_quiebre": "Posibilidades de quiebre",
    "quiebres": "Quiebres",
}

STAT_ICONS = {
    "winner": "🎯",
    "errores_no_forzados": "⚠️",
    "smash": "💥",
    "smash_winner": "🔥",
}

DEFAULT_GOOGLE_SHEET_ID = "1tcyldrxv5lZl2CKaK4-1Me73IasGlLWTVK7cuup9HRY"
SCHEDULED_MATCHES_WORKSHEET = "Partidos"
PAIR_STATS_WORKSHEET = "Estadisticas set"
AUTOSAVE_INTERVAL_SECONDS = 60
PAIR_STATS_HEADERS = [
    "Partido",
    "Set",
    "Pareja #1",
    "Pareja #2",
    "Winners #1",
    "Errores no forzados #1",
    "Smash #1",
    "Smash winner #1",
    "Winners #2",
    "Errores no forzados #2",
    "Smash #2",
    "Smash winner #2",
    "Posibilidades de quiebre #1",
    "Posibilidades de quiebre #2",
    "Quiebres #1",
    "Quiebres #2",
    "Inicio set",
    "Fin set",
    "Duracion set",
]
SCHEDULED_MATCH_HEADERS = [
    "ID",
    "Fecha",
    "Hora",
    "Partido",
    "Jugador #1",
    "Jugador #2",
    "Jugador #3",
    "Jugador #4",
    "Estado",
    "Notas",
]


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
                overscroll-behavior-y: none;
            }

            html,
            body,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                overscroll-behavior-y: none;
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

            .brand-layout {
                align-items: center;
                margin: 1rem auto 0.25rem auto;
                max-width: 760px;
            }

            [data-testid="stImage"] img {
                aspect-ratio: 1;
                border: 3px solid rgba(255, 255, 255, 0.9);
                border-radius: 50%;
                object-fit: cover;
                max-width: 260px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.24);
            }

            .brand-copy {
                padding: 0.5rem 0;
            }

            .brand-copy .court-title {
                font-size: clamp(2rem, 5vw, 3.8rem);
                line-height: 1;
            }

            .brand-title {
                color: #ffffff;
                font-size: clamp(3rem, 9vw, 6.5rem);
                font-weight: 900;
                letter-spacing: 0;
                line-height: 0.95;
                text-align: center;
                text-shadow: 0 5px 0 rgba(12, 69, 42, 0.65), 0 10px 24px rgba(0, 0, 0, 0.28);
            }

            .brand-title::after {
                background: #f4d35e;
                border-radius: 999px;
                content: "";
                display: block;
                height: 6px;
                margin: 0.8rem auto 0;
                width: 5rem;
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

            .set-timer-status {
                background: #f4d35e;
                border: 2px solid #111111;
                border-radius: 10px;
                color: #111111;
                font-size: 1.08rem;
                font-weight: 900;
                line-height: 1.25;
                padding: 10px 12px;
                text-align: center;
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
    if "stats_sheet_row_cache" not in st.session_state:
        st.session_state.stats_sheet_row_cache = {}
    if "pair_sheet_row_cache" not in st.session_state:
        st.session_state.pair_sheet_row_cache = {}

    if "stats" not in st.session_state:
        st.session_state.stats = {
            set_number: {
                quadrant: {stat: 0 for stat in STAT_KEYS}
                for quadrant in ["q1", "q2", "q3", "q4"]
            }
            for set_number in [1, 2, 3]
        }

    if "pair_stats" not in st.session_state:
        st.session_state.pair_stats = {
            set_number: {
                pair: {stat: 0 for stat in PAIR_STAT_KEYS}
                for pair in ["pair1", "pair2"]
            }
            for set_number in [1, 2, 3]
        }

    if "set_timing" not in st.session_state:
        st.session_state.set_timing = {
            set_number: {"started_at": None, "ended_at": None}
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

    if "confirm_clear_match" not in st.session_state:
        st.session_state.confirm_clear_match = False
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "scheduled_date" not in st.session_state:
        st.session_state.scheduled_date = ""
    if "scheduled_time" not in st.session_state:
        st.session_state.scheduled_time = ""
    if "scheduled_match_name" not in st.session_state:
        st.session_state.scheduled_match_name = ""
    for quadrant in ["q1", "q2", "q3", "q4"]:
        key = f"scheduled_player_{quadrant}"
        if key not in st.session_state:
            st.session_state[key] = ""
    if "scheduled_notes" not in st.session_state:
        st.session_state.scheduled_notes = ""
    if "scheduled_edit_row" not in st.session_state:
        st.session_state.scheduled_edit_row = None
    if "scheduled_edit_id" not in st.session_state:
        st.session_state.scheduled_edit_id = ""
    if "confirm_delete_scheduled_row" not in st.session_state:
        st.session_state.confirm_delete_scheduled_row = None


def inc_stat(quadrant: str, stat_key: str) -> None:
    current_set = st.session_state.selected_set
    st.session_state.stats[current_set][quadrant][stat_key] += 1


def dec_stat(quadrant: str, stat_key: str) -> None:
    current_set = st.session_state.selected_set
    st.session_state.stats[current_set][quadrant][stat_key] = max(
        0,
        st.session_state.stats[current_set][quadrant][stat_key] - 1,
    )


def set_active_quadrant(quadrant: str) -> None:
    st.session_state.active_quadrant = quadrant


def inc_pair_stat(pair: str, stat_key: str) -> None:
    current_set = st.session_state.selected_set
    st.session_state.pair_stats[current_set][pair][stat_key] += 1


def dec_pair_stat(pair: str, stat_key: str) -> None:
    current_set = st.session_state.selected_set
    st.session_state.pair_stats[current_set][pair][stat_key] = max(
        0,
        st.session_state.pair_stats[current_set][pair][stat_key] - 1,
    )


def start_set_timer() -> None:
    current_set = st.session_state.selected_set
    st.session_state.set_timing[current_set] = {
        "started_at": time.time(),
        "ended_at": None,
    }


def finish_set_timer() -> None:
    current_set = st.session_state.selected_set
    timing = st.session_state.set_timing[current_set]
    if timing["started_at"] is not None:
        timing["ended_at"] = time.time()


def get_set_duration_seconds(set_number: int) -> int | None:
    timing = st.session_state.set_timing[set_number]
    started_at = timing["started_at"]
    if started_at is None:
        return None
    ended_at = timing["ended_at"] or time.time()
    return max(0, int(ended_at - started_at))


def format_set_duration(seconds: int | None) -> str:
    if seconds is None:
        return "Sin iniciar"
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    return f"{hours:02d} h {minutes:02d} min {remaining_seconds:02d} s"


def format_set_timestamp(timestamp: float | None) -> str:
    if timestamp is None:
        return ""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def reset_set_stats(set_number: int) -> None:
    for quadrant in ["q1", "q2", "q3", "q4"]:
        for stat in STAT_KEYS:
            st.session_state.stats[set_number][quadrant][stat] = 0
    for pair in ["pair1", "pair2"]:
        for stat in PAIR_STAT_KEYS:
            st.session_state.pair_stats[set_number][pair][stat] = 0
    st.session_state.set_timing[set_number] = {
        "started_at": None,
        "ended_at": None,
    }


def reset_match_stats() -> None:
    for set_number in [1, 2, 3]:
        reset_set_stats(set_number)


def clear_match_data() -> None:
    reset_match_stats()
    st.session_state.set_timing = {
        set_number: {"started_at": None, "ended_at": None}
        for set_number in [1, 2, 3]
    }
    st.session_state.last_saved_set = None
    st.session_state.autosave_signatures = {}
    st.session_state.autosave_last_tick = 0.0
    st.session_state.confirm_clear_match = False


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
        format_set_timestamp(st.session_state.set_timing[set_number]["started_at"]),
        format_set_timestamp(st.session_state.set_timing[set_number]["ended_at"]),
        format_set_duration(get_set_duration_seconds(set_number)),
    ]


def to_pair_sheet_row_for_set(set_number: int) -> list:
    pair_one = [st.session_state.player_names["q1"], st.session_state.player_names["q2"]]
    pair_two = [st.session_state.player_names["q3"], st.session_state.player_names["q4"]]
    pair_stats = []
    for quadrants in [["q1", "q2"], ["q3", "q4"]]:
        totals = {stat: 0 for stat in STAT_KEYS}
        for quadrant in quadrants:
            for stat in STAT_KEYS:
                totals[stat] += st.session_state.stats[set_number][quadrant][stat]
        pair_stats.append(totals)

    return [
        st.session_state.match_name,
        f"SET {set_number}",
        " / ".join(pair_one),
        " / ".join(pair_two),
        pair_stats[0]["winner"],
        pair_stats[0]["errores_no_forzados"],
        pair_stats[0]["smash"],
        pair_stats[0]["smash_winner"],
        pair_stats[1]["winner"],
        pair_stats[1]["errores_no_forzados"],
        pair_stats[1]["smash"],
        pair_stats[1]["smash_winner"],
        st.session_state.pair_stats[set_number]["pair1"]["posibilidades_quiebre"],
        st.session_state.pair_stats[set_number]["pair2"]["posibilidades_quiebre"],
        st.session_state.pair_stats[set_number]["pair1"]["quiebres"],
        st.session_state.pair_stats[set_number]["pair2"]["quiebres"],
        format_set_timestamp(st.session_state.set_timing[set_number]["started_at"]),
        format_set_timestamp(st.session_state.set_timing[set_number]["ended_at"]),
        format_set_duration(get_set_duration_seconds(set_number)),
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


def get_app_password() -> str:
    try:
        configured_password = st.secrets["app_password"]
        if str(configured_password).strip():
            return str(configured_password)
    except (StreamlitSecretNotFoundError, KeyError):
        pass
    return os.getenv("POLY_STATS_PASSWORD", "").strip()


def render_login_screen() -> None:
    inject_court_styles()
    st.markdown('<div class="court-title">Poly Stats</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="court-subtitle">Ingresá la contraseña para continuar</div>',
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar", type="primary", use_container_width=True)

    if submitted:
        configured_password = get_app_password()
        if not configured_password:
            st.error("El login no está configurado. Agregá app_password en secrets.toml.")
        elif hmac.compare_digest(password, configured_password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")


def get_google_spreadsheet():
    if gspread is None or Credentials is None:
        return None

    sheet_id = resolve_google_sheet_id()
    service_account_info = get_service_account_info()
    if not sheet_id or not service_account_info:
        return None

    valid, _ = validate_service_account_info(service_account_info)
    if not valid:
        return None

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scope)
    client = gspread.authorize(credentials)
    return client.open_by_key(sheet_id)


def save_pair_stats_to_google_sheet(spreadsheet, set_number: int) -> tuple[bool, str]:
    try:
        try:
            worksheet = spreadsheet.worksheet(PAIR_STATS_WORKSHEET)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=PAIR_STATS_WORKSHEET,
                rows=1000,
                cols=len(PAIR_STATS_HEADERS),
            )
            worksheet.append_row(PAIR_STATS_HEADERS, value_input_option="RAW")

        row = to_pair_sheet_row_for_set(set_number)
        target_match = str(st.session_state.match_name).strip()
        target_set = f"SET {set_number}"
        cache_key = (target_match, set_number)
        target_row_index = st.session_state.pair_sheet_row_cache.get(cache_key)
        all_values = None

        if target_row_index is None:
            all_values = worksheet.get_all_values()
            if not all_values:
                worksheet.append_row(PAIR_STATS_HEADERS, value_input_option="RAW")
                all_values = [PAIR_STATS_HEADERS]
            elif len(all_values[0]) < len(PAIR_STATS_HEADERS):
                worksheet.update(
                    "A1:Q1",
                    [PAIR_STATS_HEADERS],
                    value_input_option="RAW",
                )

            for row_index, existing in enumerate(all_values, start=1):
                if len(existing) < 2:
                    continue
                if row_index == 1 and existing[0].strip().lower() == "partido":
                    continue
                if existing[0].strip() == target_match and existing[1].strip() == target_set:
                    target_row_index = row_index
                    st.session_state.pair_sheet_row_cache[cache_key] = row_index
                    break

        if target_row_index is not None:
            worksheet.update(
                f"A{target_row_index}:Q{target_row_index}",
                [row],
                value_input_option="RAW",
            )
            return True, f"Set {set_number} actualizado por parejas."

        worksheet.append_row(row, value_input_option="RAW")
        if all_values is not None:
            st.session_state.pair_sheet_row_cache[cache_key] = len(all_values) + 1
        return True, f"Set {set_number} guardado por parejas."
    except Exception as exc:
        return False, f"Error guardando totales por pareja: {exc}"


def get_scheduled_matches_worksheet():
    spreadsheet = get_google_spreadsheet()
    if spreadsheet is None:
        return None

    try:
        worksheet = spreadsheet.worksheet(SCHEDULED_MATCHES_WORKSHEET)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=SCHEDULED_MATCHES_WORKSHEET,
            rows=1000,
            cols=len(SCHEDULED_MATCH_HEADERS),
        )
        worksheet.append_row(SCHEDULED_MATCH_HEADERS, value_input_option="RAW")
        return worksheet

    if not worksheet.get_all_values():
        worksheet.append_row(SCHEDULED_MATCH_HEADERS, value_input_option="RAW")
    return worksheet


def fetch_scheduled_matches() -> list[dict] | None:
    try:
        worksheet = get_scheduled_matches_worksheet()
        if worksheet is None:
            return None

        rows = worksheet.get_all_records()
        matches = []
        for row_index, row in enumerate(rows, start=2):
            match_name = str(row.get("Partido", "")).strip()
            if not match_name:
                continue
            matches.append(
                {
                    "row_index": row_index,
                    "id": str(row.get("ID", "")).strip(),
                    "date": str(row.get("Fecha", "")).strip(),
                    "time": str(row.get("Hora", "")).strip(),
                    "name": match_name,
                    "players": [
                        str(row.get(f"Jugador #{index}", "")).strip()
                        for index in range(1, 5)
                    ],
                    "status": str(row.get("Estado", "Pendiente")).strip() or "Pendiente",
                    "notes": str(row.get("Notas", "")).strip(),
                }
            )
        return matches
    except Exception:
        return None


def save_scheduled_match(match: dict) -> tuple[bool, str]:
    try:
        worksheet = get_scheduled_matches_worksheet()
        if worksheet is None:
            return False, "No se pudo conectar con Google Sheets."

        row = [
            match["id"],
            match["date"],
            match["time"],
            match["name"],
            *match["players"],
            match.get("status", "Pendiente"),
            match.get("notes", ""),
        ]
        row_index = match.get("row_index")
        if row_index:
            worksheet.update(
                f"A{row_index}:J{row_index}",
                [row],
                value_input_option="RAW",
            )
            return True, "Partido actualizado en la agenda."

        worksheet.append_row(row, value_input_option="RAW")
        return True, "Partido agregado a la agenda."
    except Exception as exc:
        return False, f"Error guardando el partido: {exc}"


def delete_scheduled_match(row_index: int) -> tuple[bool, str]:
    try:
        worksheet = get_scheduled_matches_worksheet()
        if worksheet is None:
            return False, "No se pudo conectar con Google Sheets."
        worksheet.delete_rows(row_index)
        return True, "Partido eliminado de la agenda."
    except Exception as exc:
        return False, f"Error eliminando el partido: {exc}"


def load_scheduled_match(match: dict) -> None:
    st.session_state.setup_match_name = match["name"]
    for index, quadrant in enumerate(["q1", "q2", "q3", "q4"]):
        st.session_state[f"setup_player_{quadrant}"] = match["players"][index]
    st.session_state.screen = "setup"


def edit_scheduled_match(match: dict) -> None:
    st.session_state.scheduled_edit_row = match["row_index"]
    st.session_state.scheduled_edit_id = match["id"]
    st.session_state.scheduled_date = match["date"]
    st.session_state.scheduled_time = match["time"]
    st.session_state.scheduled_match_name = match["name"]
    st.session_state.scheduled_notes = match["notes"]
    for index, quadrant in enumerate(["q1", "q2", "q3", "q4"]):
        st.session_state[f"scheduled_player_{quadrant}"] = match["players"][index]


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

        target_match = str(st.session_state.match_name).strip()
        target_set = f"SET {set_number}"
        cache_key = (target_match, set_number)
        target_row_index = st.session_state.stats_sheet_row_cache.get(cache_key)
        all_values = None

        if target_row_index is None:
            # Upsert por Partido + Set: la búsqueda se hace una sola vez por sesión.
            all_values = worksheet.get_all_values()
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
                    st.session_state.stats_sheet_row_cache[cache_key] = idx
                    break

        if target_row_index is not None:
            worksheet.update(
                f"A{target_row_index}:Y{target_row_index}",
                [row],
                value_input_option="RAW",
            )
        else:
            worksheet.append_row(row, value_input_option="RAW")
            if all_values is not None:
                st.session_state.stats_sheet_row_cache[cache_key] = len(all_values) + 1

        pair_ok, pair_message = save_pair_stats_to_google_sheet(spreadsheet, set_number)
        if not pair_ok:
            return False, pair_message
    except Exception as exc:
        return False, f"Error guardando en Google Sheets: {exc}"

    if used_fallback_sheet:
        return (
            True,
            f"Set {set_number} guardado en Google Sheets (pestaña configurada no existe, se usó {worksheet.title})",
        )

    if target_row_index is not None:
        return True, f"Set {set_number} actualizado en Google Sheets y Estadisticas set (fila {target_row_index})"

    return True, f"Set {set_number} guardado en Google Sheets y Estadisticas set (nueva fila)"


def build_set_signature(set_number: int) -> tuple:
    values = []
    for quadrant in ["q1", "q2", "q3", "q4"]:
        values.append(st.session_state.player_names[quadrant])
        for stat in STAT_KEYS:
            values.append(st.session_state.stats[set_number][quadrant][stat])
    for pair in ["pair1", "pair2"]:
        for stat in PAIR_STAT_KEYS:
            values.append(st.session_state.pair_stats[set_number][pair][stat])
    values.extend(
        [
            st.session_state.set_timing[set_number]["started_at"],
            st.session_state.set_timing[set_number]["ended_at"],
        ]
    )
    return (st.session_state.match_name, set_number, *values)


def run_silent_autosave() -> None:
    # No muestra mensajes en UI. Guarda solo si cambió el set activo y pasó el intervalo.
    now = time.time()
    if now - st.session_state.autosave_last_tick < AUTOSAVE_INTERVAL_SECONDS:
        return

    set_number = st.session_state.selected_set
    signature = build_set_signature(set_number)
    saved_signature = st.session_state.autosave_signatures.get(set_number)
    if signature == saved_signature:
        return

    ok, _ = save_set_to_google_sheet(set_number)
    if ok:
        st.session_state.autosave_signatures[set_number] = signature
    st.session_state.autosave_last_tick = now


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
            on_click=set_active_quadrant,
            args=("q1",),
        ):
            pass
    with q2:
        if st.button(
            st.session_state.player_names["q2"],
            key="active_q2",
            type="primary" if st.session_state.active_quadrant == "q2" else "secondary",
            use_container_width=True,
            on_click=set_active_quadrant,
            args=("q2",),
        ):
            pass

    q3, q4 = st.columns(2)
    with q3:
        if st.button(
            st.session_state.player_names["q3"],
            key="active_q3",
            type="primary" if st.session_state.active_quadrant == "q3" else "secondary",
            use_container_width=True,
            on_click=set_active_quadrant,
            args=("q3",),
        ):
            pass
    with q4:
        if st.button(
            st.session_state.player_names["q4"],
            key="active_q4",
            type="primary" if st.session_state.active_quadrant == "q4" else "secondary",
            use_container_width=True,
            on_click=set_active_quadrant,
            args=("q4",),
        ):
            pass

    st.markdown("</div>", unsafe_allow_html=True)


def render_set_timer_controls() -> None:
    timing = st.session_state.set_timing[st.session_state.selected_set]
    timer_status_col, timer_action_col = st.columns([2, 1])
    with timer_status_col:
        if timing["started_at"] is None:
            timer_message = "Set sin iniciar"
        else:
            status = "Set en curso" if timing["ended_at"] is None else "Set terminado"
            timer_message = (
                f"{status} · Duración: "
                f"{format_set_duration(get_set_duration_seconds(st.session_state.selected_set))}"
            )
        st.markdown(f'<div class="set-timer-status">{timer_message}</div>', unsafe_allow_html=True)
    with timer_action_col:
        if timing["started_at"] is None:
            st.button("Iniciar set", on_click=start_set_timer, use_container_width=True)
        elif timing["ended_at"] is None:
            st.button("Terminar set", on_click=finish_set_timer, use_container_width=True)
        else:
            st.button("Reiniciar reloj", on_click=start_set_timer, use_container_width=True)


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

    if hasattr(st, "fragment"):
        @st.fragment(run_every="1s")
        def set_timer_fragment() -> None:
            render_set_timer_controls()

        set_timer_fragment()
    else:
        render_set_timer_controls()

    c3, c4 = st.columns(2)
    with c3:
        if st.button("Reset set actual", use_container_width=True):
            reset_set_stats(st.session_state.selected_set)
            st.success("Set reseteado")
    with c4:
        if st.button("Cerrar y guardar set", use_container_width=True):
            ok, msg = save_set_to_google_sheet(st.session_state.selected_set)
            if ok:
                st.session_state.last_saved_set = st.session_state.selected_set
                st.session_state.autosave_signatures[st.session_state.selected_set] = build_set_signature(
                    st.session_state.selected_set
                )
                st.session_state.autosave_last_tick = time.time()
                st.success(msg)
            else:
                st.warning(msg)

    c5, c6 = st.columns(2)
    with c5:
        if st.button("Actualizar pantalla", use_container_width=True):
            st.rerun()
    with c6:
        if st.button("Blanquear estadísticas", use_container_width=True):
            st.session_state.confirm_clear_match = True
            st.rerun()

    if st.session_state.confirm_clear_match:
        st.warning("Se van a borrar las estadísticas de los 3 sets. Los nombres se conservarán.")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Confirmar borrado", type="primary", use_container_width=True):
                clear_match_data()
                st.success("Estadísticas blanqueadas")
                st.rerun()
        with cancel_col:
            if st.button("Cancelar borrado", use_container_width=True):
                st.session_state.confirm_clear_match = False
                st.rerun()

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


def render_pair_stats_controls() -> None:
    set_number = st.session_state.selected_set
    pair_names = {
        "pair1": f"{st.session_state.player_names['q1']} / {st.session_state.player_names['q2']}",
        "pair2": f"{st.session_state.player_names['q3']} / {st.session_state.player_names['q4']}",
    }

    st.markdown('<div class="summary-wrap">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="summary-title">Métricas por pareja · SET {set_number}</div>',
        unsafe_allow_html=True,
    )

    pair_one_col, pair_two_col = st.columns(2)
    for column, pair in [(pair_one_col, "pair1"), (pair_two_col, "pair2")]:
        with column:
            st.markdown(f'<div class="summary-player">{pair_names[pair]}</div>', unsafe_allow_html=True)
            for stat in PAIR_STAT_KEYS:
                value = st.session_state.pair_stats[set_number][pair][stat]
                decrease_col, value_col, increase_col = st.columns([1, 3, 1])
                with decrease_col:
                    st.button(
                        "−",
                        key=f"dec_{pair}_{stat}_{set_number}",
                        on_click=dec_pair_stat,
                        args=(pair, stat),
                        use_container_width=True,
                    )
                with value_col:
                    st.markdown(
                        (
                            '<div class="stat-bubble">'
                            f'<div class="stat-label">{PAIR_STAT_LABELS[stat]}</div>'
                            f'<div class="stat-value">{value}</div>'
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                with increase_col:
                    st.button(
                        "＋",
                        key=f"inc_{pair}_{stat}_{set_number}",
                        on_click=inc_pair_stat,
                        args=(pair, stat),
                        use_container_width=True,
                    )

    st.markdown("</div>", unsafe_allow_html=True)


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

        @st.fragment(run_every="60s")
        def autosave_fragment() -> None:
            if st.session_state.screen == "match":
                run_silent_autosave()

        autosave_fragment()

    if st.session_state.match_view == "Mobile":
        render_mobile_view()
    else:
        render_court_view()

    render_pair_stats_controls()

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


def render_scheduled_matches() -> None:
    st.markdown("### Próximos partidos")
    st.caption("Podés cargarlos acá o escribirlos en la pestaña Partidos de Google Sheets.")

    matches = fetch_scheduled_matches()
    if matches is None:
        st.info("La agenda de Google Sheets todavía no está disponible.")
    elif not matches:
        st.info("No hay partidos precargados.")
    else:
        for match in matches:
            when = " · ".join(value for value in [match["date"], match["time"]] if value)
            when_label = f" · {when}" if when else ""
            with st.container(border=True):
                info_col, load_col, edit_col, delete_col = st.columns([3, 1, 1, 1])
                with info_col:
                    st.markdown(f"**{match['name']}**{when_label}")
                    st.caption(" · ".join(match["players"]))
                    if match["notes"]:
                        st.caption(match["notes"])
                with load_col:
                    if st.button(
                        "Cargar partido",
                        key=f"load_scheduled_{match['row_index']}",
                        use_container_width=True,
                    ):
                        load_scheduled_match(match)
                        st.rerun()
                with edit_col:
                    if st.button(
                        "Editar",
                        key=f"edit_scheduled_{match['row_index']}",
                        use_container_width=True,
                    ):
                        edit_scheduled_match(match)
                        st.rerun()
                with delete_col:
                    if st.button(
                        "Eliminar",
                        key=f"delete_scheduled_{match['row_index']}",
                        use_container_width=True,
                    ):
                        st.session_state.confirm_delete_scheduled_row = match["row_index"]
                        st.rerun()

    if st.session_state.confirm_delete_scheduled_row is not None:
        st.warning("Esta acción elimina el partido de la agenda y no afecta sus estadísticas guardadas.")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Confirmar eliminación", type="primary", use_container_width=True):
                ok, message = delete_scheduled_match(st.session_state.confirm_delete_scheduled_row)
                if ok:
                    st.session_state.confirm_delete_scheduled_row = None
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        with cancel_col:
            if st.button("Cancelar eliminación", use_container_width=True):
                st.session_state.confirm_delete_scheduled_row = None
                st.rerun()

    is_editing = st.session_state.scheduled_edit_row is not None
    expander_title = "Editar partido" if is_editing else "Agregar partido a la agenda"
    with st.expander(expander_title, expanded=is_editing):
        with st.form("scheduled_match_form", clear_on_submit=True):
            st.text_input("Nombre del partido", key="scheduled_match_name", placeholder="Ej. Semifinal - Club Norte")
            date_col, time_col = st.columns(2)
            with date_col:
                st.text_input("Fecha", key="scheduled_date", placeholder="2026-10-03")
            with time_col:
                st.text_input("Hora", key="scheduled_time", placeholder="18:00")

            player_col_1, player_col_2 = st.columns(2)
            with player_col_1:
                st.text_input("Jugador #1", key="scheduled_player_q1")
                st.text_input("Jugador #3", key="scheduled_player_q3")
            with player_col_2:
                st.text_input("Jugador #2", key="scheduled_player_q2")
                st.text_input("Jugador #4", key="scheduled_player_q4")
            st.text_input("Notas", key="scheduled_notes", placeholder="Cancha, torneo, observaciones...")

            submit_label = "Actualizar partido" if is_editing else "Guardar partido"
            if st.form_submit_button(submit_label, type="primary", use_container_width=True):
                name = st.session_state.scheduled_match_name.strip()
                players = [
                    st.session_state[f"scheduled_player_{quadrant}"].strip()
                    for quadrant in ["q1", "q2", "q3", "q4"]
                ]
                if not name or not all(players):
                    st.error("Completá el nombre y los 4 jugadores.")
                else:
                    ok, message = save_scheduled_match(
                        {
                            "id": (
                                f"P-{uuid4().hex[:8].upper()}"
                                if not is_editing
                                else st.session_state.scheduled_edit_id
                            ),
                            "row_index": st.session_state.scheduled_edit_row,
                            "date": st.session_state.scheduled_date.strip(),
                            "time": st.session_state.scheduled_time.strip(),
                            "name": name,
                            "players": players,
                            "status": "Pendiente",
                            "notes": st.session_state.scheduled_notes.strip(),
                        }
                    )
                    if ok:
                        st.session_state.scheduled_edit_row = None
                        st.session_state.scheduled_edit_id = ""
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)


def render_home_screen() -> None:
    """Pantalla de inicio principal con opciones para nuevo partido o histórico."""
    inject_court_styles()

    if st.button("Cerrar sesión", key="logout_button"):
        st.session_state.authenticated = False
        st.rerun()

    image_path = Path(__file__).resolve().parent / "assets" / "poly.jpeg"
    if image_path.exists():
        brand_image_col, brand_copy_col = st.columns([1, 2], vertical_alignment="center")
        with brand_image_col:
            st.image(str(image_path), use_container_width=True)
        title_container = brand_copy_col
    else:
        title_container = st.container()

    with title_container:
        st.markdown('<div class="brand-copy">', unsafe_allow_html=True)
        st.markdown('<div class="brand-title">Poly Stats</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    render_scheduled_matches()

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
    st.set_page_config(page_title="Poly Stats", page_icon="🎾", layout="wide")
    ensure_state()

    if not st.session_state.authenticated:
        render_login_screen()
        st.stop()

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
