import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { FORMATS, type Format, type RankingRow } from "@/lib/rankings";

// Rankings API — Supabase-backed overrides for the baked-in boards.
// GET  /api/rankings?format=ppr  → the latest uploaded ranking set for that
//                                  format, or { set: null } if none uploaded
//                                  (the page then falls back to the baked JSON)
// POST /api/rankings             → upload a new set. Requires the x-upload-key
//                                  header to match RANKINGS_UPLOAD_KEY. Writes
//                                  go through the Supabase service role, which
//                                  never reaches the browser.

function supabaseServer() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false } });
}

function badFormat(format: string | null): format is null {
  return !format || !FORMATS.includes(format as Format);
}

export async function GET(req: NextRequest) {
  const format = req.nextUrl.searchParams.get("format") ?? req.nextUrl.searchParams.get("scope");
  if (badFormat(format)) {
    return NextResponse.json({ error: "format must be one of ppr|halfppr|superflex" }, { status: 400 });
  }
  const supabase = supabaseServer();
  if (!supabase) {
    return NextResponse.json(
      { set: null, unconfigured: true, hint: "Supabase not configured — serving the baked-in board." },
      { status: 200 }
    );
  }

  const { data: set, error: setError } = await supabase
    .from("ranking_sets")
    .select("id, scope, filename, created_at")
    .eq("scope", format)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (setError) return NextResponse.json({ error: setError.message }, { status: 500 });
  if (!set) return NextResponse.json({ set: null });

  const { data: rows, error: rowsError } = await supabase
    .from("rankings")
    .select("rank, player, pos, pos_rank, team, bye, tier, note, flag")
    .eq("set_id", set.id)
    .order("rank", { ascending: true });

  if (rowsError) return NextResponse.json({ error: rowsError.message }, { status: 500 });
  return NextResponse.json({
    set: {
      format,
      filename: set.filename,
      updated: set.created_at,
      rows: (rows ?? []).map((r) => ({
        rank: r.rank,
        player: r.player,
        pos: r.pos,
        posRank: r.pos_rank,
        team: r.team,
        bye: r.bye,
        tier: r.tier,
        note: r.note,
        flag: r.flag,
      })),
    },
  });
}

export async function POST(req: NextRequest) {
  const uploadKey = process.env.RANKINGS_UPLOAD_KEY;
  if (!uploadKey) {
    return NextResponse.json(
      { error: "uploads_not_configured", hint: "Set RANKINGS_UPLOAD_KEY in the environment to enable uploads." },
      { status: 503 }
    );
  }
  if (req.headers.get("x-upload-key") !== uploadKey) {
    return NextResponse.json({ error: "invalid upload key" }, { status: 401 });
  }

  const supabase = supabaseServer();
  if (!supabase || !process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return NextResponse.json(
      { error: "supabase_not_configured", hint: "Set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY." },
      { status: 503 }
    );
  }

  let body: { format?: string; scope?: string; filename?: string; rows?: RankingRow[] };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const format = body.format ?? body.scope ?? null;
  if (badFormat(format)) {
    return NextResponse.json({ error: "format must be one of ppr|halfppr|superflex" }, { status: 400 });
  }
  const rows = (body.rows ?? []).filter((r) => r && typeof r.player === "string" && Number.isFinite(r.rank));
  if (rows.length === 0) {
    return NextResponse.json({ error: "no valid ranking rows in upload" }, { status: 400 });
  }
  if (rows.length > 2000) {
    return NextResponse.json({ error: "too many rows (max 2000)" }, { status: 400 });
  }

  const { data: set, error: setError } = await supabase
    .from("ranking_sets")
    .insert({ scope: format, filename: body.filename ?? null })
    .select("id, created_at")
    .single();

  if (setError || !set) {
    return NextResponse.json({ error: setError?.message ?? "failed to create ranking set" }, { status: 500 });
  }

  const { error: rowsError } = await supabase.from("rankings").insert(
    rows.map((r) => ({
      set_id: set.id,
      rank: r.rank,
      player: r.player.slice(0, 120),
      pos: r.pos?.slice(0, 10) ?? null,
      pos_rank: r.posRank?.slice(0, 10) ?? null,
      team: r.team?.slice(0, 20) ?? null,
      bye: r.bye ?? null,
      tier: r.tier?.slice(0, 40) ?? null,
      note: r.note?.slice(0, 500) ?? null,
      flag: r.flag?.slice(0, 20) ?? null,
    }))
  );

  if (rowsError) {
    await supabase.from("ranking_sets").delete().eq("id", set.id);
    return NextResponse.json({ error: rowsError.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true, setId: set.id, rows: rows.length });
}
