# app.py
import math
import streamlit as st
import pandas as pd
from serp_api_client import (
    get_serp_results,
    find_domain_rank,
    normalize_serp_results,
    normalize_target_domain,
    find_all_domain_positions,
    find_url_rank,
)
from seo_analyzer import analyze_target_vs_top
from groq_summarizer import summarize_with_groq

st.set_page_config(page_title="SEO Rank & Competitor Analyzer", layout="wide")

st.title("🔍 SEO Rank & Competitor Analyzer")

st.markdown(
    """
Enter a **keyword** and your **website (domain or URL)**.  

"""
)

with st.form("seo_form"):
    keyword = st.text_input("Keyword")
    site_input = st.text_input(
        "Your website (domain or full URL)",
        value="example.com",
        help="Examples: `example.com`, `www.example.com`, or `https://example.com/page`.",
    )
    col_a, col_b = st.columns(2)
    with col_a:
        search_depth = st.selectbox(
            "How deep should we check Google results?",
            options=[10, 20, 50, 100],
            index=0,  # default: 50
            help="This is how many results we fetch from SerpAPI. "
                 "Your rank can be anywhere inside this range.",
        )
    with col_b:
        gl = st.selectbox(
            "Google country (gl)",
            options=["in", "us", "gb", "ca", "au"],
            index=0,  # default: India
            help="Choose the country you want results for.",
        )

    submitted = st.form_submit_button("Analyze")

if submitted:
    if not keyword.strip() or not site_input.strip():
        st.error("Please enter both a keyword and a site/URL.")
    else:
        try:
            site_input_raw = site_input.strip()

            # 1) Normalize domain for domain-level work / highlighting
            normalized_domain = normalize_target_domain(site_input_raw)

            # 2) Build a URL candidate from the input (for URL-level rank)
            #    - If they gave a full URL, use as-is
            #    - If they gave a bare domain, assume https://domain/
            if site_input_raw.lower().startswith(("http://", "https://")):
                url_candidate = site_input_raw
            else:
                url_candidate = "https://" + site_input_raw.rstrip("/")

            with st.spinner(
                f"Fetching top {search_depth} results from SerpAPI for '{keyword}' ({gl.upper()})..."
            ):
                organic_results = get_serp_results(
                    keyword, num_results=search_depth, gl=gl, hl="en"
                )
                serp_rows = normalize_serp_results(organic_results)

                # Add page number for each result
                for row in serp_rows:
                    row["page"] = math.ceil(row["position"] / 10)

                # Domain-level rank (first appearance) + all positions
                domain_rank, domain_first_url = find_domain_rank(
                    organic_results, normalized_domain
                )
                domain_hits = find_all_domain_positions(
                    organic_results, normalized_domain
                )

                # URL-level rank for the thing they typed (or its https:// variant)
                url_rank, matched_url = find_url_rank(organic_results, url_candidate)

            col1, col2 = st.columns([1, 2])

            # ========== LEFT SIDE: CLEAR RANK ANSWER ==========
            with col1:
                st.subheader("🎯 Where is **your site** standing?")

                st.markdown(f"**You entered:** `{site_input_raw}`")

                # 1) URL-level ranking (what they literally typed, or https:// + that)
                st.markdown("##### 1️⃣ Ranking of this URL")
                if url_rank:
                    url_page = math.ceil(url_rank / 10)
                    st.success(
                        f"- Interpreted URL: `{url_candidate}`\n"
                        f"- Found at **position `#{url_rank}`**\n"
                        f"- On **Google page `Page {url_page}`**\n\n"
                        f"Exact URL in SERP:\n\n{matched_url}"
                    )
                else:
                    st.warning(
                        f"The URL `{url_candidate}` is **not in the top {search_depth} results** "
                        f"for '{keyword}' in {gl.upper()}."
                    )

                st.markdown("---")

                # 2) Domain-level ranking (all pages from that site)
                st.markdown(f"##### 2️⃣ Ranking of the domain `{normalized_domain}`")
                if domain_rank:
                    domain_page = math.ceil(domain_rank / 10)
                    st.success(
                        f"First appearance of domain **{normalized_domain}**:\n\n"
                        f"- Position: `#{domain_rank}`\n"
                        f"- Google page: `Page {domain_page}`\n"
                        f"- URL: {domain_first_url}"
                    )

                    if len(domain_hits) > 1:
                        st.markdown("Other pages from your domain also found:")
                        for hit in domain_hits[1:]:
                            hit_page = math.ceil(hit["position"] / 10)
                            st.write(
                                f"- `#{hit['position']}` (Page {hit_page}) – {hit['url']}"
                            )
                else:
                    st.warning(
                        f"No results from **{normalized_domain}** in the top {search_depth} results."
                    )

            # ========== RIGHT SIDE: SERP CONTEXT ==========
            with col2:
                st.subheader("🏆 Top 10 Results (for context)")

                top10_rows = serp_rows[:10]
                df = pd.DataFrame(top10_rows)

                # Mark which rows are your site by domain
                def mark_your_site(row_domain: str) -> str:
                    if (
                        row_domain == normalized_domain
                        or row_domain.endswith("." + normalized_domain)
                    ):
                        return "✅"
                    return ""

                df["is_your_site"] = df["domain"].apply(mark_your_site)

                st.dataframe(
                    df[["position", "page", "title", "domain", "link", "is_your_site"]],
                    hide_index=True,
                    use_container_width=True,
                )

                st.caption(
                    f"Showing only top 10 here for readability, "
                    f"but we searched top **{search_depth}** results for rank calculation."
                )

            # Full SERP (optional) with highlighting
            with st.expander(f"See all top {search_depth} results"):
                full_df = pd.DataFrame(serp_rows)
                full_df["is_your_site"] = full_df["domain"].apply(mark_your_site)
                st.dataframe(
                    full_df[
                        ["position", "page", "title", "domain", "link", "is_your_site"]
                    ],
                    hide_index=True,
                    use_container_width=True,
                )

            # ========== SEO ANALYSIS SECTION ==========
            st.subheader("📊 On-page SEO metrics (you vs top 3)")

            # pick best URL to analyze for you:
            # 1) exact matched URL if found
            # 2) else first domain URL
            target_url_for_analysis = None
            if matched_url:
                target_url_for_analysis = matched_url
            elif domain_first_url:
                target_url_for_analysis = domain_first_url

            top_urls = [row["link"] for row in serp_rows[:3]]

            with st.spinner("Analyzing pages (your site vs top results)..."):
                analysis = analyze_target_vs_top(
                    keyword=keyword,
                    target_url=target_url_for_analysis,
                    top_urls=top_urls,
                )

            target = analysis.get("target")
            competitors = analysis.get("competitors", [])

            metrics_rows = []

            if target:
                metrics_rows.append(
                    {
                        "who": f"YOU ({normalized_domain})",
                        "url": target["url"],
                        "score": target["score"],
                        "word_count": target["word_count"],
                        "keyword_in_title": target["keyword_in_title"],
                        "keyword_in_h1": target["keyword_in_h1"],
                        "keyword_in_meta_desc": target["keyword_in_description"],
                    }
                )

            for i, c in enumerate(competitors, start=1):
                metrics_rows.append(
                    {
                        "who": f"Top #{i}",
                        "url": c["url"],
                        "score": c["score"],
                        "word_count": c["word_count"],
                        "keyword_in_title": c["keyword_in_title"],
                        "keyword_in_h1": c["keyword_in_h1"],
                        "keyword_in_meta_desc": c["keyword_in_description"],
                    }
                )

            if metrics_rows:
                metrics_df = pd.DataFrame(metrics_rows)
                st.dataframe(metrics_df, hide_index=True, use_container_width=True)
            else:
                st.info("Could not analyze pages – maybe they failed to load.")

            # ============================
            # 🧠 Why your site is not on top
            # ============================

            # use domain_rank first, fall back to url_rank
            effective_rank = domain_rank if domain_rank else url_rank

            # If rank exists and is in top 3 → don't show explanation
            if effective_rank and effective_rank <= 3:
                st.subheader("🎉 Great news!")
                st.success(
                    f"Your site is already in the **Top {effective_rank}**, "
                    "so no improvement summary is shown."
                )
            else:
                st.subheader("🧠 Why your site is not on top")

                with st.spinner("Generating explanation (Groq)..."):
                    summary = summarize_with_groq(
                        keyword=keyword,
                        domain=normalized_domain,
                        rank=effective_rank,
                        serp_rows=serp_rows,
                        analysis=analysis,
                    )

                st.write(summary)

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()
