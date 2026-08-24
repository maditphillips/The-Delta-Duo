import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { SCOPES, type RankingRow, type Scope } from "@/lib/rankings";

// Rankings API.
// GET  /api/rankings?scope=qb   → the latest ranking set for that scope
// POST /api/rankings            → upload a new set. Requires the x-upload-key
//                                 header to match RANKINGS_UPLOAD_KEY. Writes
//                                 go through the Supabase service role, which
//                                 never reaches the browser.

function supabaseServer() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false } });
}

function badScope(scope: string | null): scope is null {
  return !scope || !SCOPES.includes(scope as Scope);
}

export async function GET(req: NextRequest) {
  const scope = req.nextUrl.searchParams.get("scope");
  if (badScope(scope)) {
    return NextResponse.json({ error: "scope must be one of overall|qb|rb|wr" }, { status: 400 });
  }
  const supabase = supabaseServer();
  if (!supabase) {
    return NextResponse.json(
      { error: "supabase_not_configured", hint: "Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY." },
      { status: 503 }
    );
  }

  const { data: set, error: setError } = await supabase
    .from("ranking_sets")
    .select("id, scope, filename, created_at")
    .eq("scope", scope)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (setError) return NextResponse.json({ error: setError.message }, { status: 500 });
  if (!set) return NextResponse.json({ set: null });

  const { data: rows, error: rowsError } = await supabase
    .from("rankings")
    .select("rank, player, team, position, note")
    .eq("set_id", set.id)
    .order("rank", { ascending: true });

  if (rowsError) return NextResponse.json({ error: rowsError.message }, { status: 500 });
  return NextResponse.json({ set: { ...set, rows: rows ?? [] } });
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

  let body: { scope?: string; filename?: string; rows?: RankingRow[] };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid JSON body" }, { status: 400 });
  }

  const scope = body.scope ?? null;
  if (badScope(scope)) {
    return NextResponse.json({ error: "scope must be one of overall|qb|rb|wr" }, { status: 400 });
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
    .insert({ scope, filename: body.filename ?? null })
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
      team: r.team?.slice(0, 20) ?? null,
      position: r.position?.slice(0, 20) ?? null,
      note: r.note?.slice(0, 500) ?? null,
    }))
  );

  if (rowsError) {
    await supabase.from("ranking_sets").delete().eq("id", set.id);
    return NextResponse.json({ error: rowsError.message }, { status: 500 });
  }

  return NextResponse.json({ ok: true, setId: set.id, rows: rows.length });
}
