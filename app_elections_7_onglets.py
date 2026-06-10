from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# -----------------------------------------------------------------------------
# CONFIGURATION PAGE
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Décisionnel Élections 2021", layout="wide")

BASE_DIR = Path(__file__).resolve().parent

st.markdown(
    """
    <style>
    .main { background-color: #f4f7f9; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #1a4a7a; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 4px;
        border: 1px solid #ddd;
        padding: 10px;
    }
    .stTabs [aria-selected="true"] { background-color: #1a4a7a !important; color: white !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# PARAMÈTRES FICHIERS
# -----------------------------------------------------------------------------
MAIN_DATA_FILE = "Liste Complète des Élus 2021-2026-04-25.csv"
SIM_TOP10_FILE = "PDN_simulation_top10_targets.csv"
SIM_TOP30_FILE = "PDN_targets_top30.csv"
SIM_TOP60_FILE = "PDN_simulation_60_sieges.csv"

# -----------------------------------------------------------------------------
# OUTILS DE NETTOYAGE
# -----------------------------------------------------------------------------
def read_csv_local(filename: str) -> pd.DataFrame:
    """Lit un CSV depuis le même dossier que l'application Streamlit."""
    path = BASE_DIR / filename
    if not path.exists():
        st.error(f"Fichier introuvable : {filename}. Mets ce fichier dans le même dossier que l'application.")
        st.stop()
    return pd.read_csv(path, sep=";", encoding="utf-8-sig")


def to_number(series: pd.Series) -> pd.Series:
    """Convertit une colonne avec virgule française / % en numérique sans planter."""
    cleaned = (
        series.astype(str)
        .str.replace("\u00a0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def clean_text_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Force les colonnes de filtre en texte pour éviter les mélanges float/str."""
    for col in cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("N/A")
                .astype(str)
                .str.strip()
                .replace({"": "N/A", "nan": "N/A", "None": "N/A"})
            )
    return df


def sorted_options(series: pd.Series) -> list[str]:
    """Retourne des options propres et triées, toujours en texte."""
    return sorted(series.dropna().astype(str).str.strip().unique(), key=str.casefold)


def normalize_simulation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonise les noms de colonnes entre top10, top30 et top60."""
    df = df.drop_duplicates().copy()

    rename_map = {
        "prefProv": "province",
        "nSieges": "seats_total",
        "quota_estimee": "quota_votes_2021",
        "quotient": "quota_votes_2021",
        "PDN_votes_2021": "pdn_votes_2021",
        "PDN_votes_simulees": "pdn_votes_simulees",
        "PDN_sieges_simules": "pdn_sieges_simules",
        "pdn_votes": "pdn_votes_2021",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    clean_text_columns(
        df,
        [
            "region",
            "province",
            "commune",
            "circonscription",
            "typeListe",
            "top_party",
            "is_accessible",
            "risk_south",
        ],
    )

    numeric_candidates = [
        "seats_total",
        "total_votes_2021",
        "quota_votes_2021",
        "pdn_votes_target_90pct_quota",
        "pdn_votes_target_100pct_quota",
        "pdn_votes_target_110pct_quota",
        "txParticipation_pct",
        "votes_total_parties",
        "top_share",
        "enp",
        "pdn_votes_2021",
        "pdn_share",
        "pdn_rank",
        "score",
        "pdn_votes_simulees",
        "pdn_sieges_simules",
    ]
    for col in numeric_candidates:
        if col in df.columns:
            df[col] = to_number(df[col])

    return df


@st.cache_data
def get_clean_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Données électorales réelles
    df_raw = read_csv_local(MAIN_DATA_FILE)

    for col in ["votes_parti", "taux_participation", "total_votes"]:
        if col in df_raw.columns:
            df_raw[col] = to_number(df_raw[col])

    text_cols = [
        "region",
        "province",
        "commune",
        "circonscription",
        "nom_parti_fr",
        "nom_fr",
        "nom_ar",
        "type_election",
        "sous_type_election",
    ]
    df_raw = clean_text_columns(df_raw, text_cols)

    # Simulations PDN séparées
    df_top10 = normalize_simulation_columns(read_csv_local(SIM_TOP10_FILE))
    df_top30 = normalize_simulation_columns(read_csv_local(SIM_TOP30_FILE))
    df_top60 = normalize_simulation_columns(read_csv_local(SIM_TOP60_FILE))

    return df_raw, df_top10, df_top30, df_top60


df_raw, df_top10, df_top30, df_top60 = get_clean_data()

# -----------------------------------------------------------------------------
# FILTRES HIÉRARCHIQUES SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.header("🎯 Filtres Stratégiques")

reg_opt = sorted_options(df_raw["region"])
sel_reg = st.sidebar.multiselect("Région", reg_opt)

mask_p = df_raw["region"].isin(sel_reg) if sel_reg else df_raw["region"].notnull()
prov_opt = sorted_options(df_raw.loc[mask_p, "province"])
sel_prov = st.sidebar.multiselect("Province", prov_opt)

mask_c = df_raw["province"].isin(sel_prov) if sel_prov else mask_p
comm_opt = sorted_options(df_raw.loc[mask_c, "commune"])
sel_comm = st.sidebar.multiselect("Commune", comm_opt)

mask_circ = df_raw["commune"].isin(sel_comm) if sel_comm else mask_c
circ_opt = sorted_options(df_raw.loc[mask_circ, "circonscription"])
sel_circ = st.sidebar.multiselect("Circonscription", circ_opt)

parti_opt = sorted_options(df_raw["nom_parti_fr"])
sel_parti = st.sidebar.multiselect("Parti", parti_opt)

search = st.sidebar.text_input("🔍 Recherche Candidat (Nom)")


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if sel_reg:
        d = d[d["region"].isin(sel_reg)]
    if sel_prov:
        d = d[d["province"].isin(sel_prov)]
    if sel_comm:
        d = d[d["commune"].isin(sel_comm)]
    if sel_circ:
        d = d[d["circonscription"].isin(sel_circ)]
    if sel_parti:
        d = d[d["nom_parti_fr"].isin(sel_parti)]
    if search:
        d = d[
            d["nom_fr"].str.contains(search, case=False, na=False)
            | d["nom_ar"].str.contains(search, case=False, na=False)
        ]
    return d


def filter_simulation(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if sel_reg and "region" in d.columns:
        d = d[d["region"].isin(sel_reg)]
    if sel_prov and "province" in d.columns:
        d = d[d["province"].isin(sel_prov)]
    if sel_circ and "circonscription" in d.columns:
        d = d[d["circonscription"].isin(sel_circ)]
    return d

# -----------------------------------------------------------------------------
# ONGLET ANALYSE ÉLECTORALE
# -----------------------------------------------------------------------------
def display_analysis(tab, subtype: str, key_prefix: str) -> None:
    with tab:
        st.header(subtype)

        data = df_raw[df_raw["sous_type_election"] == subtype]
        data = filter_dataframe(data)

        geo_key = ["region", "province", "commune", "circonscription"]
        unique_territories = data.drop_duplicates(subset=geo_key)
        party_votes = data.drop_duplicates(subset=geo_key + ["nom_parti_fr"])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Élus / lignes", len(data))
        c2.metric("Territoires", len(unique_territories))

        total_v = unique_territories["total_votes"].sum() if "total_votes" in unique_territories.columns else 0
        c3.metric("Total votes uniques", f"{int(total_v) if pd.notna(total_v) else 0:,}")

        avg_p = unique_territories["taux_participation"].mean() * 100 if "taux_participation" in unique_territories.columns else None
        c4.metric("Participation moy.", f"{avg_p:.2f}%" if pd.notna(avg_p) else "N/A")

        st.write("---")

        col_g, col_d = st.columns([2, 1])

        with col_g:
            st.subheader("Performance des partis - total voix")
            if party_votes.empty or "votes_parti" not in party_votes.columns:
                st.info("Aucune donnée disponible pour ce graphique.")
            else:
                votes_per_party = (
                    party_votes.groupby("nom_parti_fr", as_index=False)["votes_parti"]
                    .sum()
                    .sort_values("votes_parti", ascending=False)
                    .head(12)
                )
                fig = px.bar(
                    votes_per_party,
                    x="votes_parti",
                    y="nom_parti_fr",
                    orientation="h",
                    color_discrete_sequence=["#1a4a7a"],
                    labels={"votes_parti": "Voix", "nom_parti_fr": ""},
                )
                fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_party_votes")

        with col_d:
            st.subheader("Répartition géographique")
            geo_dist = data["region"].value_counts().reset_index()
            geo_dist.columns = ["region", "nombre"]

            if geo_dist.empty:
                st.info("Aucune donnée disponible pour ce graphique.")
            else:
                fig_geo = px.pie(
                    geo_dist,
                    names="region",
                    values="nombre",
                    title="Répartition par région",
                    hole=0.35,
                )
                fig_geo.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_geo, use_container_width=True, key=f"{key_prefix}_geo_distribution")

        st.subheader("Tableau de bord détaillé")
        useful = [
            c
            for c in data.columns
            if data[c].notna().any() and c not in ["type_election", "sous_type_election"]
        ]
        st.dataframe(data[useful], use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ONGLET SIMULATION PDN
# -----------------------------------------------------------------------------
def best_available_columns(df: pd.DataFrame, wanted: list[str]) -> list[str]:
    return [col for col in wanted if col in df.columns]


def display_simulation(tab, df: pd.DataFrame, title: str, key_prefix: str) -> None:
    with tab:
        st.header(title)
        data = filter_simulation(df)

        if data.empty:
            st.warning("Aucune donnée disponible avec les filtres actuels.")
            return

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Circonscriptions", len(data))

        seats = data["seats_total"].sum() if "seats_total" in data.columns else None
        c2.metric("Sièges / potentiel", f"{int(seats) if pd.notna(seats) else 0}")

        if "pdn_votes_target_100pct_quota" in data.columns:
            avg_target = data["pdn_votes_target_100pct_quota"].mean()
            c3.metric("Objectif moyen 100%", f"{int(avg_target) if pd.notna(avg_target) else 0:,}")
        elif "pdn_votes_simulees" in data.columns:
            total_sim = data["pdn_votes_simulees"].sum()
            c3.metric("Votes PDN simulés", f"{int(total_sim) if pd.notna(total_sim) else 0:,}")
        elif "quota_votes_2021" in data.columns:
            avg_quota = data["quota_votes_2021"].mean()
            c3.metric("Quota moyen", f"{int(avg_quota) if pd.notna(avg_quota) else 0:,}")
        else:
            c3.metric("Objectif", "N/A")

        if "score" in data.columns:
            score_avg = data["score"].mean()
            c4.metric("Score moyen", f"{score_avg:.1f}%" if pd.notna(score_avg) else "N/A")
        elif "pdn_sieges_simules" in data.columns:
            sim_seats = data["pdn_sieges_simules"].sum()
            c4.metric("Sièges PDN simulés", f"{int(sim_seats) if pd.notna(sim_seats) else 0}")
        elif "pdn_votes_target_110pct_quota" in data.columns:
            high_potential = data[data["pdn_votes_target_110pct_quota"] > 30000]
            c4.metric("Zones à fort enjeu", len(high_potential))
        else:
            c4.metric("Indicateur", "N/A")

        st.write("---")

        col_1, col_2 = st.columns([1, 1])

        with col_1:
            st.subheader("Objectifs / potentiel par circonscription")

            scenario_cols = best_available_columns(
                data,
                [
                    "pdn_votes_target_90pct_quota",
                    "pdn_votes_target_100pct_quota",
                    "pdn_votes_target_110pct_quota",
                ],
            )

            if scenario_cols and "circonscription" in data.columns:
                sim_melted = data.melt(
                    id_vars=["circonscription"],
                    value_vars=scenario_cols,
                    var_name="Scenario",
                    value_name="Voix",
                )
                fig_sim = px.line(
                    sim_melted,
                    x="circonscription",
                    y="Voix",
                    color="Scenario",
                    markers=True,
                )
                fig_sim.update_layout(height=450, xaxis_tickangle=-45)
                st.plotly_chart(fig_sim, use_container_width=True, key=f"{key_prefix}_scenario_line")

            elif "pdn_votes_simulees" in data.columns and "circonscription" in data.columns:
                chart_df = data.sort_values("pdn_votes_simulees", ascending=False).head(30)
                fig_sim = px.bar(
                    chart_df,
                    x="pdn_votes_simulees",
                    y="circonscription",
                    orientation="h",
                    labels={"pdn_votes_simulees": "Votes PDN simulés", "circonscription": ""},
                )
                fig_sim.update_layout(height=600, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_sim, use_container_width=True, key=f"{key_prefix}_votes_bar")

            elif "score" in data.columns and "circonscription" in data.columns:
                chart_df = data.sort_values("score", ascending=False).head(30)
                fig_sim = px.bar(
                    chart_df,
                    x="score",
                    y="circonscription",
                    orientation="h",
                    labels={"score": "Score", "circonscription": ""},
                )
                fig_sim.update_layout(height=600, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_sim, use_container_width=True, key=f"{key_prefix}_score_bar")

            else:
                st.info("Pas assez de colonnes numériques pour produire un graphique.")

        with col_2:
            st.subheader("Classement stratégique")

            preferred_cols = best_available_columns(
                data,
                [
                    "region",
                    "province",
                    "circonscription",
                    "typeListe",
                    "seats_total",
                    "quota_votes_2021",
                    "pdn_votes_target_100pct_quota",
                    "pdn_votes_simulees",
                    "pdn_sieges_simules",
                    "pdn_votes_2021",
                    "pdn_share",
                    "score",
                    "top_party",
                    "is_accessible",
                ],
            )

            sort_candidates = [
                "score",
                "pdn_votes_target_100pct_quota",
                "pdn_votes_simulees",
                "quota_votes_2021",
            ]
            sort_col = next((col for col in sort_candidates if col in data.columns), None)
            table_df = data[preferred_cols].copy() if preferred_cols else data.copy()
            if sort_col:
                table_df = table_df.sort_values(sort_col, ascending=False)

            st.dataframe(table_df, hide_index=True, use_container_width=True)

        st.subheader("Données complètes")
        st.dataframe(data, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# STRUCTURE DES 7 ONGLETS - ORDRE DEMANDÉ
# -----------------------------------------------------------------------------
tab_leg_locale, tab_leg_regionale, tab_regionale, tab_communale, tab_top10, tab_top30, tab_top60 = st.tabs(
    [
        "0 📍 Législative-Locale",
        "1 🌐 Législative-Régionale",
        "2 🗺️ Régionale",
        "3 🏠 Communale",
        "4 📈 Simulation Top10",
        "5 📊 Simulation Top30",
        "6 🚀 Simulation Top60",
    ]
)

# Onglets élections réelles
display_analysis(tab_leg_locale, "Législative-Locale", "legislative_locale")
display_analysis(tab_leg_regionale, "Législative-Régionale", "legislative_regionale")
display_analysis(tab_regionale, "Régionale", "regionale")
display_analysis(tab_communale, "Communale", "communale")

# Onglets simulations PDN
display_simulation(tab_top10, df_top10, "Simulation PDN - Top10", "simulation_top10")
display_simulation(tab_top30, df_top30, "Simulation PDN - Top30", "simulation_top30")
display_simulation(tab_top60, df_top60, "Simulation PDN - Top60", "simulation_top60")
