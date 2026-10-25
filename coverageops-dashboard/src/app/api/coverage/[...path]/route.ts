import { NextRequest, NextResponse } from "next/server";

const backend = process.env.BACKEND_URL || "http://127.0.0.1:8002";

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: Context) {
  const { path } = await context.params;
  if (!path?.length || path.some((segment) => !/^[a-zA-Z0-9_-]+$/.test(segment))) {
    return NextResponse.json({ detail: "Invalid API path" }, { status: 400 });
  }
  const target = `${backend}/coverage/${path.join("/")}`;
  try {
    const method = request.method;
    const body = method === "POST" ? await request.text() : undefined;
    const response = await fetch(target, {
      method,
      headers: { ...(body ? { "Content-Type": "application/json" } : {}) },
      body,
      cache: "no-store",
    });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") || "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: `Cannot reach FastAPI at ${backend}. Start the backend on port 8002.` },
      { status: 502 },
    );
  }
}

export async function GET(req: NextRequest, ctx: Context) { return proxy(req, ctx); }
export async function POST(req: NextRequest, ctx: Context) { return proxy(req, ctx); }
