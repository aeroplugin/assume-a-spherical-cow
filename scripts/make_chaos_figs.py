"""Generate chaos-chapter figures as PNGs using only the standard library.
usage: python3 -I make_chaos_figs.py <outdir>
"""
import sys, zlib, struct, math

def write_png(path, w, h, rgb_rows):
    raw = b"".join(b"\x00" + bytes(row) for row in rgb_rows)
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)

def render(density, w, h, ink=(43, 78, 192), gamma=0.45, sat=None):
    m = max(max(r) for r in density) or 1
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            d = density[y][x]
            if sat:
                a = min(1.0, (d / sat) ** 0.6) if d else 0.0
            else:
                a = min(1.0, ((d / m) ** gamma) * 1.15) if d else 0.0
            for c in ink:
                row.append(int(round(255 * (1 - a) + c * a)))
        rows.append(row)
    return rows

def logistic(out):
    W, H = 1400, 820
    r0, r1 = 2.6, 4.0
    dens = [[0] * W for _ in range(H)]
    for i in range(W):
        r = r0 + (r1 - r0) * i / (W - 1)
        x = 0.5
        for _ in range(1200):
            x = r * x * (1 - x)
        for _ in range(900):
            x = r * x * (1 - x)
            y = int((1 - x) * (H - 1))
            if 0 <= y < H:
                dens[y][i] += 1
    write_png(out + "/logistic-bifurcation.png", W, H, render(dens, W, H, sat=5))

def lorenz(out):
    W, H = 1200, 1000
    s, rho, b = 10.0, 28.0, 8.0 / 3.0
    def f(v):
        x, y, z = v
        return (s * (y - x), x * (rho - z) - y, x * y - b * z)
    v = (1.0, 1.0, 1.0)
    dt = 0.004
    dens = [[0] * W for _ in range(H)]
    for n in range(400000):
        k1 = f(v)
        k2 = f(tuple(v[i] + 0.5 * dt * k1[i] for i in range(3)))
        k3 = f(tuple(v[i] + 0.5 * dt * k2[i] for i in range(3)))
        k4 = f(tuple(v[i] + dt * k3[i] for i in range(3)))
        v = tuple(v[i] + dt / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) for i in range(3))
        if n < 2000:
            continue
        px = int((v[0] + 24) / 48 * (W - 1))
        py = int((1 - (v[2] - 0) / 52) * (H - 1))
        if 0 <= px < W and 0 <= py < H:
            dens[py][px] += 1
    write_png(out + "/lorenz.png", W, H, render(dens, W, H, ink=(178, 58, 43), gamma=0.35))

if __name__ == "__main__":
    out = sys.argv[1]
    logistic(out)
    lorenz(out)
    print("done")
