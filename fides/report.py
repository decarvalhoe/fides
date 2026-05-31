"""Construction et écriture du rapport (JSON + Markdown lisible)."""
from __future__ import annotations

import json
import os


def build_report(wi, analysis, plan, before, after, null, outputs,
                 profile, used_reference, lmeta=None) -> dict:
    null_clean = {k: v for k, v in null.items() if k != "residual"}
    summary = {
        "input": wi.path,
        "format": f"{wi.samplerate} Hz / {wi.channels} ch / {wi.subtype}",
        "duration_s": round(wi.duration, 1),
        "truncated_header": wi.truncated,
        "active_channels": analysis.active_indices,
        "unique_active_channels": analysis.unique_active_indices,
        "primary_channel": analysis.primary_index,
        "profile": profile.get("name"),
        "loudness_before": before,
        "loudness_after": after,
        "loudness_gain_db": (lmeta or {}).get("gain_db"),
        "loudness_mode": (lmeta or {}).get("mode", "ebu" if lmeta is None else "linéaire"),
        "tp_limited": (lmeta or {}).get("tp_limited"),
        "dynamics_preserved": (lmeta or {}).get("mode") != "limiter" if lmeta else None,
        "null_residual_rel_db": null_clean.get("residual_rel_db"),
        "null_interpretation": null_clean.get("interpretation"),
        "used_reference_match": used_reference,
        "outputs": outputs,
    }
    return {
        "summary": summary,
        "analysis": analysis.to_dict(),
        "plan": plan,
        "measures": {"before": before, "after": after, "null": null_clean, "loudness": lmeta},
        "guardrails": {
            "philosophy": "traitement minimal, soustractif, transparent ; ne pas dénaturer",
            "null_test": "résidu écrit dans null_residual.wav (écouter ce qui a été ajouté/retiré)",
            "ab": "_pre_master.wav = nettoyé sans loudness (A/B vs original) ; master.wav = livrable",
            "ai_denoise": "AUCUN débruiteur IA voix (DeepFilterNet etc.) — ils dénaturent les cordes",
            "loudness": "gain linéaire plafonné true-peak -> dynamique (LRA) préservée (EBU R128 s2 2023)",
        },
    }


def write_json(report: dict, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return path


def _fmt(v):
    return "—" if v is None else v


def write_md(report: dict, path: str) -> str:
    s = report["summary"]
    a = report["analysis"]
    plan = report["plan"]
    lm = report["measures"].get("loudness")
    L = []
    L.append(f"# Rapport de mastering Fides —`{os.path.basename(s['input'])}`\n")
    L.append(f"- **Format** : {s['format']} · durée {s['duration_s']} s"
             + (" · ⚠️ en-tête tronqué (réparé à la lecture)" if s["truncated_header"] else ""))
    L.append(f"- **Profil** : {s['profile']}")
    L.append(f"- **Canaux actifs** : {s['active_channels']} · uniques : {s['unique_active_channels']} "
             f"· **primaire** : ch{s['primary_channel']}")
    L.append("")
    L.append("## Loudness (avant → après)\n")
    b, af = s["loudness_before"], s["loudness_after"]
    L.append("| | LUFS intégré | Peak (dBFS) | True-peak (dBTP) |")
    L.append("|---|---|---|---|")
    L.append(f"| Original (ch{s['primary_channel']}) | {_fmt(b['lufs'])} | {b['peak_dbfs']} | {b['true_peak_dbtp']} |")
    L.append(f"| Master | {_fmt(af['lufs'])} | {af['peak_dbfs']} | {af['true_peak_dbtp']} |")
    L.append("")
    if lm:
        note = ""
        if lm.get("tp_limited"):
            note = (" · ⚠️ plafonné par le true-peak : master sous la cible "
                    f"({lm.get('target_lufs')} LUFS) mais **dynamique intacte** "
                    "(les plateformes normalisent vers le haut)")
        L.append(f"_Gain master {lm['gain_db']:+.2f} dB · mode {lm.get('mode')}{note}_\n")
    L.append(f"**Null-test** : résidu relatif {s['null_residual_rel_db']} dB — "
             f"*{s['null_interpretation']}* (écouter `null_residual.wav`)\n")

    L.append("## Canaux\n")
    L.append("| ch | rôle | peak | RMS | bruit p05 | DR | clip | centroïde |")
    L.append("|---|---|---|---|---|---|---|---|")
    for c in a["channels"]:
        dup = f"→ch{c['duplicate_of']}" if c.get("duplicate_of") is not None else ""
        L.append(f"| {c['index']} | {c['role']}{dup} | {c['peak_dbfs']} | {c['rms_dbfs']} "
                 f"| {c['noise_floor_dbfs']} | {c['dynamic_range_db']} | {c['clipped_runs']} "
                 f"| {c['centroid_hz']} Hz |")
    L.append("")

    L.append("## Chaîne appliquée (par canal traité)\n")
    for c, pc in plan["channels"].items():
        L.append(f"**ch{c}** : " + " · ".join(pc["steps"]))
    L.append("")
    lo = plan["loudness"]
    L.append(f"_Cible profil : {lo.get('target_lufs')} LUFS / true-peak {lo.get('true_peak_dbtp')} dBTP_\n")

    L.append("## Garde-fous (ne pas dénaturer)\n")
    for k, v in report["guardrails"].items():
        L.append(f"- **{k}** : {v}")
    L.append("")
    L.append("## Sorties\n")
    for k, v in s["outputs"].items():
        L.append(f"- `{k}` : {v}")
    L.append("")

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return path


def write_html(report: dict, path: str) -> str:
    """Rapport HTML autonome (sans dépendance externe)."""
    s = report["summary"]
    a = report["analysis"]
    plan = report["plan"]
    b, af = s["loudness_before"], s["loudness_after"]

    def rows_channels():
        out = []
        for c in a["channels"]:
            dup = f"&rarr;ch{c['duplicate_of']}" if c.get("duplicate_of") is not None else ""
            out.append(f"<tr><td>{c['index']}</td><td>{c['role']}{dup}</td>"
                       f"<td>{c['peak_dbfs']}</td><td>{c['rms_dbfs']}</td>"
                       f"<td>{c['noise_floor_dbfs']}</td><td>{c['dynamic_range_db']}</td>"
                       f"<td>{c['clipped_runs']}</td><td>{c['centroid_hz']}</td></tr>")
        return "\n".join(out)

    chain = "".join(f"<li><b>ch{c}</b> : {' · '.join(pc['steps'])}</li>"
                    for c, pc in plan["channels"].items())
    _spec = s["outputs"].get("report_spectrum")
    spec_html = (f'<h2>Preuve — spectre original vs master</h2>'
                 f'<img src="{os.path.basename(_spec)}" alt="spectre original vs master Fides" '
                 f'style="width:100%;border:1px solid #e3e3e3;border-radius:4px">') if _spec else ""
    html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Fides —{os.path.basename(s['input'])}</title>
<style>
 body{{font:15px/1.5 system-ui,Segoe UI,Arial;margin:2rem auto;max-width:880px;color:#1a1a1a}}
 h1{{font-size:1.4rem}} h2{{font-size:1.05rem;margin-top:1.6rem;border-bottom:1px solid #eee;padding-bottom:.2rem}}
 table{{border-collapse:collapse;width:100%;font-size:.9rem}} td,th{{border:1px solid #e3e3e3;padding:4px 8px;text-align:right}}
 th:first-child,td:first-child,td:nth-child(2){{text-align:left}}
 .ok{{color:#127a2b}} .warn{{color:#b25e00}} code{{background:#f5f5f5;padding:1px 4px;border-radius:3px}}
 .muted{{color:#666}}
</style></head><body>
<h1>Rapport de mastering Fides —<code>{os.path.basename(s['input'])}</code></h1>
<p class="muted">{s['format']} · {s['duration_s']} s · mode <b>{s.get('mode','?')}</b>
{' · <span class="warn">en-tête tronqué (réparé)</span>' if s['truncated_header'] else ''}
· profil <b>{s['profile']}</b> · primaire ch{s['primary_channel']}</p>

<h2>Loudness</h2>
<table><tr><th></th><th>LUFS</th><th>Peak dBFS</th><th>True-peak dBTP</th></tr>
<tr><td>Original (ch{s['primary_channel']})</td><td>{b['lufs']}</td><td>{b['peak_dbfs']}</td><td>{b['true_peak_dbtp']}</td></tr>
<tr><td>Master</td><td>{af['lufs']}</td><td>{af['peak_dbfs']}</td><td>{af['true_peak_dbtp']}</td></tr></table>
<p>Gain {s.get('loudness_gain_db')} dB · mode {s.get('loudness_mode')} ·
{'<span class="warn">plafonné true-peak (dynamique intacte)</span>' if s.get('tp_limited') else '<span class="ok">cible atteinte</span>'}</p>
<p><b>Null-test</b> : résidu {s['null_residual_rel_db']} dB — <i>{s['null_interpretation']}</i></p>
{spec_html}

<h2>Canaux</h2>
<table><tr><th>ch</th><th>rôle</th><th>peak</th><th>RMS</th><th>bruit</th><th>DR</th><th>clip</th><th>centroïde</th></tr>
{rows_channels()}</table>

<h2>Chaîne appliquée</h2><ul>{chain}</ul>

<h2>Garde-fous</h2><ul>
{''.join(f'<li><b>{k}</b> : {v}</li>' for k, v in report['guardrails'].items())}
</ul>
</body></html>"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
