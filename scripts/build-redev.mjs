// data/seoul_jeongbi_raw.csv (data.go.kr 15097425 "서울특별시_서울시 정비사업 데이터") 를
// 주소→좌표 변환해 data/redevelopment.json 으로 굽는 1회성 스크립트. 빌드 파이프라인 아님.
//
// 사용법:
//   1. https://www.data.go.kr/data/15097425/fileData.do 에서 CSV 다운로드
//   2. data/seoul_jeongbi_raw.csv 로 저장
//   3. KAKAO_REST_KEY=... node scripts/build-redev.mjs
//
// ponytail: 분기별 수동 실행. 데이터 출처(공공포털)가 안정적인 API를 열면 그때 자동화.

import { readFileSync, writeFileSync } from "node:fs";

const REST_KEY = process.env.KAKAO_REST_KEY;
if (!REST_KEY) { console.error("KAKAO_REST_KEY 환경변수가 필요합니다."); process.exit(1); }

const RAW = "data/seoul_jeongbi_raw.csv";
const OUT = "data/redevelopment.json";

// --- CSV 읽기 (data.go.kr CSV는 보통 EUC-KR) ---
const buf = readFileSync(RAW);
let text;
try { text = new TextDecoder("euc-kr", { fatal: true }).decode(buf); }
catch { text = new TextDecoder("utf-8").decode(buf); }

function parseCsv(s) {
    const rows = [];
    let row = [], field = "", q = false;
    for (let i = 0; i < s.length; i++) {
        const c = s[i];
        if (q) {
            if (c === '"' && s[i + 1] === '"') { field += '"'; i++; }
            else if (c === '"') q = false;
            else field += c;
        } else if (c === '"') q = true;
        else if (c === ",") { row.push(field); field = ""; }
        else if (c === "\n" || c === "\r") {
            if (c === "\r" && s[i + 1] === "\n") i++;
            row.push(field); rows.push(row); row = []; field = "";
        } else field += c;
    }
    if (field || row.length) { row.push(field); rows.push(row); }
    return rows.filter(r => r.some(v => v.trim()));
}

const rows = parseCsv(text);
const header = rows.shift().map(h => h.trim());
const col = name => header.findIndex(h => h.includes(name));
const ci = {
    name: col("정비구역명"), gu: col("시군구명"), dong: col("법정동명"),
    bunji: col("번지"), type: col("정비유형"), stage: col("시행단계"),
};
if (ci.gu < 0 || ci.dong < 0) { console.error("예상한 컬럼(시군구명/법정동명)을 못 찾음. 헤더:", header); process.exit(1); }

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function geocode(query) {
    const url = "https://dapi.kakao.com/v2/local/search/address.json?query=" + encodeURIComponent(query);
    const res = await fetch(url, { headers: { Authorization: "KakaoAK " + REST_KEY } });
    if (!res.ok) { console.warn("  geocode HTTP", res.status, query); return null; }
    const j = await res.json();
    const d = j.documents && j.documents[0];
    return d ? { lat: +d.y, lng: +d.x } : null;
}

const out = [];
let ok = 0, fail = 0;
for (const r of rows) {
    const gu = (r[ci.gu] || "").trim();
    const dong = (r[ci.dong] || "").trim();
    const bunji = ci.bunji >= 0 ? (r[ci.bunji] || "").trim() : "";
    if (!gu || !dong) continue;
    const addr = `서울특별시 ${gu} ${dong} ${bunji}`.trim();
    const g = await geocode(addr) || await geocode(`서울특별시 ${gu} ${dong}`);
    await sleep(120); // 카카오 REST 초당 제한 여유
    if (!g) { fail++; console.warn("  좌표 실패:", addr); continue; }
    ok++;
    out.push({
        name: (ci.name >= 0 ? r[ci.name] : "").trim() || `${dong} 정비구역`,
        type: (ci.type >= 0 ? r[ci.type] : "").trim(),
        status: (ci.stage >= 0 ? r[ci.stage] : "").trim(),
        addr, gu,
        lat: +g.lat.toFixed(6), lng: +g.lng.toFixed(6),
    });
}

writeFileSync(OUT, JSON.stringify(out, null, 0) + "\n");
console.log(`완료: ${ok}건 저장, ${fail}건 좌표 실패 → ${OUT}`);
