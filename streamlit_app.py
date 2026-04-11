import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import StringIO

st.set_page_config(
    page_title="Statistiques OIML - Controle Metrologique",
    page_icon="⚖️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# OIML R 87 - Erreurs Maximales Tolerees (EMT / TNE)
# Source : OIML R 87 Ed. 2016 - Tableau 1
# ---------------------------------------------------------------------------

OIML_TABLE = [
    {"Qn_min": 5,     "Qn_max": 50,    "TNE_pct": 9.0,   "TNE_g": None,  "label": "9 % de Qn"},
    {"Qn_min": 50,    "Qn_max": 100,   "TNE_pct": None,  "TNE_g": 4.5,   "label": "4,5 g"},
    {"Qn_min": 100,   "Qn_max": 200,   "TNE_pct": 4.5,   "TNE_g": None,  "label": "4,5 % de Qn"},
    {"Qn_min": 200,   "Qn_max": 300,   "TNE_pct": None,  "TNE_g": 9.0,   "label": "9 g"},
    {"Qn_min": 300,   "Qn_max": 500,   "TNE_pct": 3.0,   "TNE_g": None,  "label": "3 % de Qn"},
    {"Qn_min": 500,   "Qn_max": 1000,  "TNE_pct": None,  "TNE_g": 15.0,  "label": "15 g"},
    {"Qn_min": 1000,  "Qn_max": 10000, "TNE_pct": 1.5,   "TNE_g": None,  "label": "1,5 % de Qn"},
    {"Qn_min": 10000, "Qn_max": 15000, "TNE_pct": None,  "TNE_g": 150.0, "label": "150 g"},
    {"Qn_min": 15000, "Qn_max": 50000, "TNE_pct": 1.0,   "TNE_g": None,  "label": "1 % de Qn"},
]


def get_tne(qn: float) -> float | None:
    """Retourne l'EMT (TNE) en grammes pour une quantite nominale Qn (g)."""
    for row in OIML_TABLE:
        if row["Qn_min"] <= qn <= row["Qn_max"]:
            if row["TNE_g"] is not None:
                return row["TNE_g"]
            return round(row["TNE_pct"] / 100.0 * qn, 4)
    return None


def compute_statistics(measurements: np.ndarray, qn: float, tne: float) -> dict:
    """Calcule les statistiques et verifie la conformite OIML R 87."""
    n = len(measurements)
    mean = float(np.mean(measurements))
    std = float(np.std(measurements, ddof=1)) if n > 1 else 0.0
    minimum = float(np.min(measurements))
    maximum = float(np.max(measurements))
    median = float(np.median(measurements))

    # Seuils OIML
    t1 = qn - tne          # Seuil T1 : defectueux
    t2 = qn - 2 * tne      # Seuil T2 : doublement defectueux

    defectives_t1 = measurements[measurements < t1]
    defectives_t2 = measurements[measurements < t2]

    pct_t1 = len(defectives_t1) / n * 100

    # Critere 1 : Moyenne >= Qn
    crit1_ok = mean >= qn

    # Critere 2 : <= 2 % des unites < T1 = Qn - TNE
    crit2_ok = pct_t1 <= 2.0

    # Critere 3 : Aucune unite < T2 = Qn - 2*TNE
    crit3_ok = len(defectives_t2) == 0

    conformant = crit1_ok and crit2_ok and crit3_ok

    # Cpk (spec limite inferieure = Qn - TNE, pas de limite superieure)
    cpk = (mean - t1) / (3 * std) if std > 0 else float("inf")

    return {
        "n": n,
        "mean": mean,
        "std": std,
        "min": minimum,
        "max": maximum,
        "median": median,
        "t1": t1,
        "t2": t2,
        "nb_t1": len(defectives_t1),
        "pct_t1": pct_t1,
        "nb_t2": len(defectives_t2),
        "crit1_ok": crit1_ok,
        "crit2_ok": crit2_ok,
        "crit3_ok": crit3_ok,
        "conformant": conformant,
        "cpk": cpk,
    }


def parse_input(text: str) -> np.ndarray | None:
    """Parse une saisie texte : valeurs separees par virgule, point-virgule ou saut de ligne."""
    import re
    values = re.split(r"[,;\s\n]+", text.strip())
    try:
        arr = np.array([float(v.replace(",", ".")) for v in values if v.strip()])
        return arr if len(arr) > 0 else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

st.title("⚖️ Controle metrologique — Statistiques OIML R 87")
st.markdown(
    "Calcul de la **moyenne** et de l'**ecart-type** d'un echantillon de poids "
    "et verification de la conformite selon la reglementation **OIML R 87** "
    "(quantites en preemballages)."
)

st.divider()

# Tableau de reference OIML
with st.expander("Tableau de reference OIML R 87 — Erreurs Maximales Tolerees (EMT)", expanded=False):
    df_ref = pd.DataFrame([
        {
            "Quantite nominale Qn (g)": f"{r['Qn_min']} < Qn ≤ {r['Qn_max']}"
            if r["Qn_min"] != 5
            else f"{r['Qn_min']} ≤ Qn ≤ {r['Qn_max']}",
            "EMT (TNE)": r["label"],
        }
        for r in OIML_TABLE
    ])
    st.dataframe(df_ref, use_container_width=True, hide_index=True)

st.divider()

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("Parametres")

    qn = st.number_input(
        "Quantite nominale Qn (g)",
        min_value=5.0,
        max_value=50000.0,
        value=500.0,
        step=1.0,
        help="Masse nominale indiquee sur l'emballage, en grammes.",
    )

    tne = get_tne(qn)

    if tne is not None:
        st.success(f"**EMT (TNE) = {tne:.4g} g** pour Qn = {qn} g")
        st.info(
            f"- Seuil T1 (defectueux) : **{qn - tne:.4g} g**  \n"
            f"- Seuil T2 (doublement defectueux) : **{qn - 2 * tne:.4g} g**"
        )
    else:
        st.error(
            f"Qn = {qn} g est hors du domaine d'application OIML R 87 (5 g a 50 000 g)."
        )

    st.subheader("Saisie des mesures")
    input_method = st.radio(
        "Mode de saisie",
        ["Saisie manuelle", "Import CSV / fichier texte"],
        horizontal=True,
    )

    measurements = None

    if input_method == "Saisie manuelle":
        raw = st.text_area(
            "Mesures (g)",
            placeholder="Ex: 498.5, 501.2, 499.8, 502.1, 497.3\n(separateur : virgule, point-virgule ou saut de ligne)",
            height=180,
        )
        if raw.strip():
            measurements = parse_input(raw)
            if measurements is None:
                st.error("Format non reconnu. Utilisez des nombres separes par virgule, point-virgule ou saut de ligne.")
    else:
        uploaded = st.file_uploader(
            "Fichier CSV ou TXT (une valeur par ligne ou separateur virgule/point-virgule)",
            type=["csv", "txt"],
        )
        if uploaded is not None:
            content = uploaded.read().decode("utf-8", errors="ignore")
            measurements = parse_input(content)
            if measurements is None:
                st.error("Impossible de lire les donnees. Verifiez le format du fichier.")

with col_right:
    st.subheader("Resultats statistiques")

    if tne is None:
        st.warning("Veuillez saisir une quantite nominale valide (5 g a 50 000 g).")
    elif measurements is None or len(measurements) == 0:
        st.info("Saisissez vos mesures a gauche pour obtenir les resultats.")
    else:
        stats = compute_statistics(measurements, qn, tne)

        # ---- KPI principaux -----------------------------------------------
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Nombre de mesures (n)", stats["n"])
        k2.metric("Moyenne x̄ (g)", f"{stats['mean']:.4g}")
        k3.metric("Ecart-type s (g)", f"{stats['std']:.4g}")
        k4.metric("Cpk", f"{stats['cpk']:.3f}" if stats['cpk'] != float('inf') else "∞")

        k5, k6, k7, k8 = st.columns(4)
        k5.metric("Minimum (g)", f"{stats['min']:.4g}")
        k6.metric("Maximum (g)", f"{stats['max']:.4g}")
        k7.metric("Mediane (g)", f"{stats['median']:.4g}")
        k8.metric("Etendue (g)", f"{stats['max'] - stats['min']:.4g}")

        st.divider()

        # ---- Conformite OIML -----------------------------------------------
        st.subheader("Conformite OIML R 87")

        def badge(ok: bool) -> str:
            return "✅ Conforme" if ok else "❌ Non conforme"

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Critere 1 — Moyenne**")
            st.markdown(f"x̄ = {stats['mean']:.4g} g ≥ Qn = {qn} g")
            st.markdown(badge(stats["crit1_ok"]))

        with c2:
            st.markdown("**Critere 2 — Defectueux (T1)**")
            st.markdown(
                f"{stats['nb_t1']} unite(s) < {stats['t1']:.4g} g  \n"
                f"({stats['pct_t1']:.1f} % ≤ 2,0 % requis)"
            )
            st.markdown(badge(stats["crit2_ok"]))

        with c3:
            st.markdown("**Critere 3 — Doublement defectueux (T2)**")
            st.markdown(
                f"{stats['nb_t2']} unite(s) < {stats['t2']:.4g} g  \n"
                "(0 tolere)"
            )
            st.markdown(badge(stats["crit3_ok"]))

        verdict_color = "success" if stats["conformant"] else "error"
        verdict_text = (
            "LOT CONFORME — Les trois criteres OIML R 87 sont satisfaits."
            if stats["conformant"]
            else "LOT NON CONFORME — Au moins un critere OIML R 87 n'est pas satisfait."
        )
        getattr(st, verdict_color)(verdict_text)

        st.divider()

        # ---- Graphique -------------------------------------------------------
        st.subheader("Distribution des mesures")

        fig = go.Figure()

        # Histogramme
        fig.add_trace(
            go.Histogram(
                x=measurements,
                name="Mesures",
                marker_color="#4C8BF5",
                opacity=0.75,
                autobinx=True,
            )
        )

        y_max_hint = max(1, stats["n"] // 3)

        # Ligne Qn
        fig.add_vline(x=qn, line_dash="solid", line_color="green",
                      annotation_text=f"Qn = {qn} g", annotation_position="top right")

        # Ligne T1
        fig.add_vline(x=stats["t1"], line_dash="dash", line_color="orange",
                      annotation_text=f"T1 = {stats['t1']:.4g} g", annotation_position="top left")

        # Ligne T2
        fig.add_vline(x=stats["t2"], line_dash="dash", line_color="red",
                      annotation_text=f"T2 = {stats['t2']:.4g} g", annotation_position="top left")

        # Ligne moyenne
        fig.add_vline(x=stats["mean"], line_dash="dot", line_color="blue",
                      annotation_text=f"x̄ = {stats['mean']:.4g} g", annotation_position="top right")

        fig.update_layout(
            xaxis_title="Masse (g)",
            yaxis_title="Nombre d'unites",
            legend_title="Legende",
            height=380,
            margin=dict(l=20, r=20, t=30, b=20),
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---- Tableau des mesures hors tolerance ------------------------------
        if stats["nb_t1"] > 0:
            st.subheader("Unites hors tolerance T1")
            idx_t1 = np.where(measurements < stats["t1"])[0]
            df_bad = pd.DataFrame({
                "N° mesure": idx_t1 + 1,
                "Masse (g)": measurements[idx_t1],
                "Ecart / Qn (g)": measurements[idx_t1] - qn,
                "T2 depasse": measurements[idx_t1] < stats["t2"],
            })
            df_bad["T2 depasse"] = df_bad["T2 depasse"].map({True: "Oui ❌", False: "Non"})
            st.dataframe(df_bad, use_container_width=True, hide_index=True)
