#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a minimal step-by-step browser review wizard for a policy queue.

One decision per screen: adopt the audit pick, adopt the rule-teacher pick,
or type your own target number, then press Enter or click "确认下一条".
Progress is persisted in the browser (localStorage); the result is exported
as JSONL for ``convert_policy_review_queue.py``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


FEATURE_SHORT = {
    "candidate_suspicion": "怀疑",
    "candidate_public_pressure": "公开压力",
    "candidate_wolf_belief": "狼信念",
    "candidate_seer_belief": "预言家信念",
    "candidate_is_sheriff_nomination": "归票",
    "candidate_is_provisional_vote": "暂定票",
    "candidate_in_trusted_set": "可信",
    "candidate_is_known_good": "已知好人",
    "candidate_is_known_wolf": "已知狼",
    "candidate_is_wolf_teammate": "狼队友",
}


def _top_action(distribution: dict[str, float]) -> str | None:
    if not distribution:
        return None

    def tie_key(action_id: str) -> int:
        suffix = str(action_id).split(":")[-1]
        return -int(suffix) if suffix.isdigit() else 0

    return max(
        distribution,
        key=lambda action_id: (float(distribution[action_id]), tie_key(action_id)),
    )


def _canonical_action(action_id: object) -> str:
    text = str(action_id)
    return text if text.startswith("exile_vote:") else f"exile_vote:{text}"


def _join_references(
    queue: list[dict[str, object]],
    teacher_path: Path | None,
    labels_path: Path | None,
) -> list[dict[str, object]]:
    """Attach teacher and audit references without touching the queue schema."""

    teacher_by_digest: dict[str, dict[str, object]] = {}
    if teacher_path is not None:
        for line in teacher_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            teacher_by_digest[str(record["observation_digest"])] = record
    label_by_digest: dict[str, dict[str, object]] = {}
    if labels_path is not None:
        for line in labels_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            label = json.loads(line)
            label_by_digest[str(label["observation_digest"])] = label

    for row in queue:
        digest = str(row["observation_digest"])
        teacher = teacher_by_digest.get(digest)
        label = label_by_digest.get(digest)
        teacher_distribution = (
            dict(teacher["rule_probabilities"]) if teacher is not None else {}
        )
        audit_distribution = (
            dict(label["target_distribution"]) if label is not None else {}
        )
        row["_teacher_top"] = _canonical_action(_top_action(teacher_distribution))
        row["_teacher_top_prob"] = (
            float(teacher_distribution.get(row["_teacher_top"].split(":")[-1], 0.0))
            if row["_teacher_top"] is not None
            else None
        )
        row["_audit_top"] = _canonical_action(_top_action(audit_distribution))
        row["_audit_top_prob"] = (
            float(audit_distribution.get(row["_audit_top"], 0.0))
            if row["_audit_top"] is not None
            else None
        )
        row["_audit_confidence"] = (
            float(label["confidence"]) if label is not None else None
        )

        teacher_candidates = {
            str(candidate["target_id"]): candidate
            for candidate in (teacher or {}).get("candidates", [])
        }
        feature_names = [str(name) for name in (teacher or {}).get("feature_names", [])]
        for candidate in row["candidates"]:
            target_id = str(candidate["target_id"])
            teacher_candidate = teacher_candidates.get(target_id)
            action_id = str(candidate["action_id"])
            candidate["teacher_prob"] = float(
                teacher_distribution.get(target_id, 0.0)
            )
            candidate["audit_prob"] = float(audit_distribution.get(action_id, 0.0))
            values = teacher_candidate.get("feature_values", []) if teacher_candidate else []
            features: dict[str, float] = {}
            for short_name, feature_name in FEATURE_SHORT.items():
                if feature_name in feature_names:
                    index = feature_names.index(feature_name)
                    if index < len(values):
                        features[short_name] = float(values[index])
            candidate["features"] = features
    return queue


def render(queue: list[dict[str, object]]) -> str:
    payload = json.dumps(
        {
            "rows": queue,
            "featureShort": FEATURE_SHORT,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V5 标签审阅向导</title>
<style>
:root{--bg:#f4f6fb;--panel:#ffffff;--line:#d9e0ec;--text:#1d2733;--muted:#66738a;--good:#128a5b;--goodbg:#e5f6ee;--wolf:#b3424f;--wolfbg:#fbe9eb;--blue:#1f5fc4;--bluebg:#e8f0fd;--amber:#9a6a08;--amberbg:#fdf3df}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
button,input{font:inherit;color:inherit}.app{max-width:900px;margin:0 auto;padding:20px 16px 60px}
.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.title{font-size:22px;font-weight:700}.sub{color:var(--muted);font-size:13px}
.bar{height:10px;background:#e3e8f2;border-radius:99px;overflow:hidden;margin:10px 0 6px}.bar i{display:block;height:100%;background:linear-gradient(90deg,#1f5fc4,#2f9e6e)}
.progress-text{color:var(--muted);font-size:13px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 1px 3px rgba(20,35,60,.06)}
.tag{display:inline-block;padding:2px 9px;border-radius:99px;font-size:12px;margin-right:6px}
.tag.good{background:var(--goodbg);color:var(--good)}.tag.wolf{background:var(--wolfbg);color:var(--wolf)}.tag.blue{background:var(--bluebg);color:var(--blue)}.tag.amber{background:var(--amberbg);color:var(--amber)}
.scenario{background:#f8fafd;border:1px dashed var(--line);border-radius:10px;padding:10px 12px;margin:12px 0;color:#33415c}
.quick{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
.quick button{border:1.5px solid var(--line);background:var(--panel);border-radius:11px;padding:12px;cursor:pointer;text-align:left}
.quick button:hover{border-color:var(--blue)}
.quick .which{font-size:12px;color:var(--muted);display:block}.quick .pick{font-size:19px;font-weight:700;display:block;margin-top:3px}
.quick .prob{font-size:12px;color:var(--muted);display:block;margin-top:3px}
.cand{width:100%;border:1.5px solid var(--line);background:var(--panel);border-radius:11px;padding:10px 12px;margin:6px 0;cursor:pointer;text-align:left;display:block}
.cand:hover{border-color:var(--blue)}.cand.sel{border-color:var(--good);background:var(--goodbg)}
.cand .num{font-size:22px;font-weight:800;color:var(--blue)}
.cand .flag{font-size:12px;color:var(--amber)}
.cand .meta{font-size:12px;color:var(--muted);margin-top:3px}
.row-choose{display:flex;gap:10px;align-items:center;margin:14px 0;flex-wrap:wrap}
.row-choose input{width:120px;padding:11px 12px;border:1.5px solid var(--line);border-radius:10px;font-size:18px;font-weight:700;text-align:center}
.row-choose input:focus{outline:none;border-color:var(--blue)}
.primary{background:var(--blue);color:#fff;border:none;border-radius:10px;padding:12px 22px;font-size:16px;font-weight:700;cursor:pointer}
.primary:hover{filter:brightness(1.08)}
.ghost{background:var(--panel);border:1.5px solid var(--line);border-radius:10px;padding:11px 16px;cursor:pointer;color:var(--muted)}
.ghost:hover{color:var(--text);border-color:var(--muted)}
.foot{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap}
.hint{color:var(--muted);font-size:13px}
.details{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
.details summary{cursor:pointer;color:var(--muted);font-size:13px}
.kv{font-size:13px;color:#33415c;margin:4px 0}
.done-screen{text-align:center;padding:30px 10px}
.done-screen h2{font-size:24px}
.big{font-size:15px;padding:14px 24px}
.bulk{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.bulk button{border:1.5px solid var(--line);background:var(--panel);border-radius:9px;padding:9px 13px;cursor:pointer}
.bulk button:hover{border-color:var(--blue)}
.hidden{display:none!important}
@media(max-width:560px){.quick{grid-template-columns:1fr}.app{padding:12px}}
</style></head><body><main class="app">
<section class="top"><div><div class="title">V5 标签审阅向导</div><div class="sub">每屏一条：选一个目标号，回车确认。进度自动保存在本机浏览器。</div></div>
<div><button id="exportBtn" class="ghost">导出结果 JSONL</button> <button id="resetBtn" class="ghost">重新开始</button></div></section>
<div class="bar"><i id="barFill" style="width:0%"></i></div><div class="progress-text" id="progressText"></div>

<section id="startPanel" class="panel">
  <h2>怎么用（三步）</h2>
  <p>① 填你的审阅者 ID（默认 <b>tonystark</b>）；② 逐条选择目标：可以直接点<b>“采纳审计建议”</b>或<b>“采纳 teacher”</b>，也可以自己输入目标号；③ 点<b>“确认下一条”</b>（或直接按回车），直到完成，最后点右上角<b>“导出结果 JSONL”</b>。</p>
  <div class="row-choose"><label>你的审阅者 ID：</label><input id="sourceInput" value="tonystark" style="width:200px;text-align:left"></div>
  <div class="bulk">
    <button id="bulkAudit">一键采纳全部审计建议</button>
    <button id="bulkTeacher">一键采纳全部 teacher 建议</button>
    <button id="startBtn" class="primary">开始 / 继续审阅</button>
  </div>
</section>

<section id="reviewPanel" class="panel hidden">
  <div><span class="tag good" id="factionTag"></span><span class="tag blue">第 <span id="dayText"></span> 天 · <span id="phaseText"></span> · actor <span id="actorText"></span></span></div>
  <div class="scenario" id="scenario"></div>
  <div class="quick" id="quickRow"></div>
  <div id="candList"></div>
  <div class="row-choose"><label>我的选择（目标号）：</label><input id="numberInput" type="number" min="1" max="12" placeholder="如 9"><button id="confirmBtn" class="primary">确认下一条 ↵</button></div>
  <div class="foot">
    <div class="hint" id="navHint"></div>
    <div><button id="skipBtn" class="ghost">跳过此条</button></div>
  </div>
  <details class="details"><summary>查看特征与理由（高级，可编辑）</summary>
    <div class="kv" id="featureBlock"></div>
    <div class="row-choose"><label>理由：</label><input id="rationaleInput" type="text" style="width:auto;min-width:320px;text-align:left;font-size:14px;font-weight:400"></div>
  </details>
</section>

<section id="donePanel" class="panel done-screen hidden">
  <h2>全部完成 🎉</h2>
  <p id="doneSummary"></p>
  <p class="sub">请点击“导出结果 JSONL”保存文件，然后告诉我文件路径，我来完成后续转换、合并与重训。</p>
  <button id="exportBtn2" class="primary big">导出结果 JSONL</button>
</section>
</main><script>
const DATA = __QUEUE__;
const KEY = "agent-town-review-wizard-v3";
let rows = DATA.rows.map(x => ({...x, _done:false, _source:""}));
let sourceId = "tonystark";
let index = 0;
let started = false;
const $ = id => document.getElementById(id);
const esc = v => String(v ?? "").replace(/[&<>"']/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[m]));
function persist(){ try{ localStorage.setItem(KEY, JSON.stringify({sourceId, started, rows: rows.map(r=>({observation_digest:r.observation_digest, preferred_action_id:r.preferred_action_id, target_distribution:r.target_distribution, confidence:r.confidence, weight:r.weight, source_id:r.source_id, rationale:r.rationale, tags:r.tags, _done:r._done, _source:r._source}))})) }catch(e){} }
function load(){ try{ const s=JSON.parse(localStorage.getItem(KEY)); if(s){ if(typeof s.sourceId==="string") sourceId=s.sourceId; started=!!s.started; const by={}; s.rows.forEach(r=>by[r.observation_digest]=r); rows.forEach(r=>{ const saved=by[r.observation_digest]; if(saved){ Object.assign(r, saved); } }); } }catch(e){} }
load();
const isDone = r => !!(r.preferred_action_id || r.target_distribution);
function nextPending(from){ for(let i=from+1;i<rows.length;i++){ if(!isDone(rows[i])) return i; } for(let i=0;i<rows.length;i++){ if(!isDone(rows[i])) return i; } return -1; }
function applyChoice(row, actionId, source){ const n=String(actionId).split(":")[1]; row.preferred_action_id=String(actionId); row.target_distribution=null; row.confidence=1.0; row.weight=1.0; row.source_id=sourceId; row._source=source; row.tags=["logic_conflict_review","human_review","adopted_"+source]; row.rationale=`人工审阅确认：${row.faction==="good"?"好人":"狼人"} actor ${row.actor_id} 第 ${row.day} 天选择 ${n} 号（来源：${source}）。`; row._done=true; }
function topN(){ return {audit: rows[index]._audit_top, teacher: rows[index]._teacher_top}; }
function renderProgress(){ const done=rows.filter(isDone).length; $("barFill").style.width=(done/rows.length*100)+"%"; $("progressText").textContent=`进度：已完成 ${done} / ${rows.length} 条`; }
function pct(v){ return v==null ? "" : (v*100).toFixed(1)+"%"; }
function candidateLine(c){
  const flags=[]; if(+c.sole_consistent_seer>0) flags.push("唯一一致预言家"); if(+c.logic_conflict>0) flags.push("公开冲突");
  const f=c.features||{}; const feat=DATA.featureShort;
  const parts=Object.keys(feat).filter(k=>f[k]!=null && +f[k]!==0).map(k=>`${feat[k]} ${+f[k]>1?+f[k].toFixed(2):(+f[k]*100).toFixed(0)+"%"}`);
  return `<button class="cand" data-n="${c.target_id}"><span class="num">${c.target_id} 号</span> ${flags.map(x=>`<span class="flag">${x}</span>`).join(" ")}<div class="meta">teacher ${pct(c.teacher_prob)} · 审计 ${pct(c.audit_prob)}${parts.length?" · "+esc(parts.join("，")):""}</div></button>`;
}
function renderReview(){
  const x=rows[index];
  $("factionTag").textContent=x.faction==="good"?"好人":"狼人";
  $("factionTag").className="tag "+(x.faction==="good"?"good":"wolf");
  $("dayText").textContent=x.day; $("phaseText").textContent=x.phase; $("actorText").textContent=x.actor_id;
  const sole=x.candidates.filter(c=>+c.sole_consistent_seer>0).map(c=>c.target_id);
  const conf=x.candidates.filter(c=>+c.logic_conflict>0).map(c=>c.target_id);
  let scene=`这是第 ${x.day} 天 ${x.phase} 阶段，${x.faction==="good"?"好人":"狼人"} ${x.actor_id} 号从合法放逐候选中选择目标。`;
  if(sole.length) scene+=` 唯一一致预言家候选：${sole.join("、")} 号。`;
  if(conf.length) scene+=` 公开逻辑冲突候选：${conf.join("、")} 号。`;
  if(!sole.length&&!conf.length) scene+=` 本条没有结构化硬冲突标记。`;
  $("scenario").textContent=scene;
  const q=$("quickRow"); q.innerHTML="";
  const add=(label,which,action,p,cls)=>{ if(!action) return; const b=document.createElement("button"); b.className=cls||""; b.innerHTML=`<span class="which">${esc(label)}</span><span class="pick">投 ${String(action).split(":")[1]} 号</span><span class="prob">${pct(p)}</span>`; b.onclick=()=>{ $("numberInput").value=String(action).split(":")[1]; selectHighlight(); }; q.appendChild(b); };
  add("采纳审计建议","audit",x._audit_top,x._audit_top_prob);
  add("采纳 teacher（规则）","teacher",x._teacher_top,x._teacher_top_prob);
  $("candList").innerHTML=x.candidates.map(candidateLine).join("");
  document.querySelectorAll(".cand").forEach(el=>el.onclick=()=>{ $("numberInput").value=el.dataset.n; selectHighlight(); });
  $("rationaleInput").value=x.rationale||"";
  const fb=$("featureBlock"); fb.innerHTML="";
  x.candidates.forEach(c=>{ const f=c.features||{}; const parts=Object.keys(DATA.featureShort).filter(k=>f[k]!=null).map(k=>`${DATA.featureShort[k]}=${f[k]}`); fb.innerHTML+=`<div>${c.target_id} 号：${parts.join("  ")||"（无特征）"}</div>`; });
  $("numberInput").focus(); $("numberInput").select();
}
function selectHighlight(){ const v=$("numberInput").value; document.querySelectorAll(".cand").forEach(el=>el.classList.toggle("sel", el.dataset.n===v)); }
function confirmCurrent(){
  const x=rows[index]; const v=$("numberInput").value.trim();
  if(!v){ alert("请先选择目标号（点按钮或输入数字）"); return; }
  const legal=x.candidates.some(c=>String(c.target_id)===v);
  if(!legal){ alert(`目标 ${v} 号不在合法候选中`); return; }
  applyChoice(x, "exile_vote:"+v, "manual"); persist(); next();
}
function next(){ const n=nextPending(index); if(n>=0){ index=n; render(); } else { renderDone(); } }
function renderDone(){
  $("startPanel").classList.add("hidden"); $("reviewPanel").classList.add("hidden"); $("donePanel").classList.remove("hidden");
  const done=rows.filter(isDone).length;
  $("doneSummary").textContent=`已确认 ${done} / ${rows.length} 条（其中采纳审计 ${rows.filter(r=>r._source==="audit").length}、teacher ${rows.filter(r=>r._source==="teacher").length}、手填 ${rows.filter(r=>r._source==="manual").length}）。`;
  renderProgress();
}
function render(){ renderProgress(); if(rows.every(isDone) && rows.length){ renderDone(); return; }
  if(!started){ $("reviewPanel").classList.add("hidden"); $("donePanel").classList.add("hidden"); $("startPanel").classList.remove("hidden"); return; }
  $("startPanel").classList.add("hidden"); $("donePanel").classList.add("hidden"); $("reviewPanel").classList.remove("hidden");
  renderReview();
}
function exportJsonl(){
  const filled=rows.filter(isDone);
  if(!filled.length){ alert("还没有已确认的条目"); return; }
  const clean=filled.map(x=>{ const o={...x}; ["_done","_source","_teacher_top","_teacher_top_prob","_audit_top","_audit_top_prob","_audit_confidence"].forEach(k=>delete o[k]); return o; });
  const text=clean.map(x=>JSON.stringify(x)).join("\\n")+"\\n";
  const blob=new Blob([text],{type:"application/x-ndjson"}), a=document.createElement("a");
  a.href=URL.createObjectURL(blob); a.download="reviewed_policy_queue.jsonl"; a.click(); URL.revokeObjectURL(a.href);
}
$("startBtn").onclick=()=>{ sourceId=$("sourceInput").value.trim()||"tonystark"; started=true; persist(); index=nextPending(-1); if(index<0){ renderDone(); } else { render(); } };
$("confirmBtn").onclick=confirmCurrent;
$("skipBtn").onclick=()=>{ index=nextPending(index); if(index>=0) render(); else renderDone(); };
$("numberInput").oninput=selectHighlight;
$("exportBtn").onclick=exportJsonl; $("exportBtn2").onclick=exportJsonl;
$("resetBtn").onclick=()=>{ if(confirm("清除本机进度并重新开始？")){ try{localStorage.removeItem(KEY)}catch(e){} location.reload(); } };
$("bulkAudit").onclick=()=>{ if(confirm("把全部尚未确认的条目都采纳“审计建议”？（已确认的不变）")){ rows.forEach(r=>{ if(!isDone(r)&&r._audit_top) applyChoice(r, r._audit_top, "audit"); }); persist(); render(); } };
$("bulkTeacher").onclick=()=>{ if(confirm("把全部尚未确认的条目都采纳“teacher 建议”？（已确认的不变）")){ rows.forEach(r=>{ if(!isDone(r)&&r._teacher_top) applyChoice(r, r._teacher_top, "teacher"); }); persist(); render(); } };
document.onkeydown=e=>{ if(e.key==="Enter" && !$("reviewPanel").classList.contains("hidden")){ e.preventDefault(); confirmCurrent(); } };
render();
</script></body></html>""".replace("__QUEUE__", payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a minimal offline review wizard for a policy queue."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--teacher",
        type=Path,
        help="optional rule-teacher JSONL to show teacher recommendations",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        help="optional converted label JSONL to show audit recommendations",
    )
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise SystemExit("review queue is empty")
    rows = _join_references(rows, args.teacher, args.labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(rows), encoding="utf-8")
    print(
        json.dumps(
            {"rows": len(rows), "output": str(args.output)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
