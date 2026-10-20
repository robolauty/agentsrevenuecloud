#!/usr/bin/env python3
"""Valida MANIFIESTO-POC.md (formato de references/manifiesto-poc.md).

Adaptación de nespon-brief-to-demo/scripts/validate_manifest.py para la ruta POC:
sustituye NEC/ESC (necesidad/escena, con wow obligatorio) por NEC/HIP/EXP
(necesidad/hipótesis/paso de experimento, sin wow). CMP y DAT se validan igual.

Uso:
  python3 validate_manifest_poc.py MANIFIESTO-POC.md          # validación de diseño (Fase 1)
  python3 validate_manifest_poc.py MANIFIESTO-POC.md --gate   # además exige APROBADO (Fase 3)
Sale con 1 si hay errores.
"""
import re
import sys

RESP = {"IA", "IA+Revisión", "Persona"}
NIVEL = {"🟢", "🔵", "🟠"}
ESTADO = {"Pendiente", "Hecho", "Bloqueado", "Persona pendiente"}
SYSTEM_FIELDS = ["LastStageChangeDate", "IsClosed", "IsWon", "HasOpenActivity", "LastActivityDate",
                 "LastViewedDate", "SystemModstamp", "IsEscalated", "ClosedDate"]
ABS_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d{1,2}/\d{1,2}/20\d\d\b")
ID = lambda p: re.compile(r"\b" + p + r"-\d+\b")


def rows(text, prefix):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells and re.fullmatch(prefix + r"-\d+", cells[0]):
            out.append(cells)
    return out


def section(text, title_start):
    m = re.search(r"^## " + re.escape(title_start) + r".*?$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def main(path, gate):
    text = open(path, encoding="utf-8").read()
    E, W = [], []

    m = re.search(r"\*\*Estado de revisión:\*\*\s*([A-ZÁÉÍÓÚ]+)", text)
    estado = m.group(1) if m else None
    if estado not in ("BORRADOR", "APROBADO"):
        E.append("Cabecera: 'Estado de revisión' debe ser BORRADOR o APROBADO")
    if estado == "APROBADO":
        rv = re.search(r"\*\*Revisado por:\*\*\s*([^·\n]+)", text)
        if not rv or rv.group(1).strip() in ("—", "-", ""):
            E.append("APROBADO sin 'Revisado por'")
    if gate and estado != "APROBADO":
        E.append("PUERTA: el manifiesto no está APROBADO; no se puede ejecutar el experimento")

    if not re.search(r"\*\*Incertidumbre:\*\*\s*\S", text):
        E.append("Cabecera: falta 'Incertidumbre' (la pregunta que hay que responder)")

    nec = rows(text, "NEC")
    nec_ids = {r[0] for r in nec}
    if not nec:
        W.append("No hay necesidades/dudas de origen (NEC-n)")
    for r in nec:
        if len(r) < 3 or r[2] not in ("Brief", "Supuesto"):
            W.append(f"{r[0]}: Origen debería ser 'Brief' o 'Supuesto'")

    hip = rows(text, "HIP")
    hip_ids = {r[0] for r in hip}
    if not hip:
        E.append("No hay hipótesis (HIP-n)")
    for r in hip:
        if len(r) < 4 or r[3] in ("—", "-", ""):
            E.append(f"{r[0]}: sin criterio de éxito")
        if len(r) < 5 or r[4] in ("—", "-", ""):
            W.append(f"{r[0]}: sin condición de 'si no se cumple / no concluyente'")

    exp = rows(text, "EXP")
    exp_ids = {r[0] for r in exp}
    covered = set()
    for r in exp:
        refs = set(ID("HIP").findall(r[2] if len(r) > 2 else ""))
        if not refs:
            E.append(f"{r[0]}: no se liga a ninguna hipótesis")
        for x in refs - hip_ids:
            E.append(f"{r[0]}: cita {x}, que no existe")
        covered |= refs
        if len(r) < 6 or r[4] in ("—", "-", "") or r[5] in ("—", "-", ""):
            E.append(f"{r[0]}: falta 'Resultado esperado' o 'Evidencia requerida'")
    for x in sorted(hip_ids - covered):
        E.append(f"{x}: ninguna hipótesis tiene pasos de experimento (EXP) que la prueben")
    if not exp:
        E.append("No hay pasos de experimento (EXP-n)")

    cmp_rows = rows(text, "CMP")
    cmp_ids = [r[0] for r in cmp_rows]
    for d in {x for x in cmp_ids if cmp_ids.count(x) > 1}:
        E.append(f"{d} definido varias veces")
    tareas = section(text, "4.")
    by_exp = set()
    lvl = {"🟢": 0, "🔵": 0, "🟠": 0}
    resp = {"IA": 0, "IA+Revisión": 0, "Persona": 0}
    for r in cmp_rows:
        if len(r) < 10:
            E.append(f"{r[0]}: faltan columnas (esperadas 10)")
            continue
        _, e, _, _, spec, nivel, rsp, motivo, tam, est = r[:10]
        for x in ID("EXP").findall(e):
            by_exp.add(x)
            if x not in exp_ids:
                E.append(f"{r[0]}: paso {x} no existe")
        nv = next((n for n in NIVEL if n in nivel), None)
        if not nv:
            E.append(f"{r[0]}: nivel debe ser 🟢/🔵/🟠")
        else:
            lvl[nv] += 1
        if rsp not in RESP:
            E.append(f"{r[0]}: responsable '{rsp}' no válido (IA | IA+Revisión | Persona)")
        else:
            resp[rsp] += 1
        sin_motivo = motivo in ("—", "-", "")
        if rsp in ("Persona", "IA+Revisión") and sin_motivo:
            E.append(f"{r[0]}: {rsp} sin motivo")
        if nv == "🟠" and sin_motivo:
            E.append(f"{r[0]}: 🟠 sin motivo de impacto")
        if rsp == "Persona" and not re.search(r"^### " + re.escape(r[0]) + r"\b", tareas, re.M):
            E.append(f"{r[0]}: es Persona y no tiene bloque en '4. Tareas de persona'")
        if tam not in ("S", "M", "L"):
            W.append(f"{r[0]}: tamaño debería ser S, M o L")
        if est not in ESTADO:
            W.append(f"{r[0]}: estado '{est}' no reconocido")
        if spec in ("—", "-", ""):
            E.append(f"{r[0]}: sin especificación")
    for x in sorted(exp_ids - by_exp):
        W.append(f"{x}: ningún componente lo construye")

    dat = rows(text, "DAT")
    for r in dat:
        line = " | ".join(r)
        for f in SYSTEM_FIELDS:
            if re.search(r"\b" + f + r"\b", line):
                E.append(f"{r[0]}: usa campo de sistema '{f}'")
        if ABS_DATE.search(line):
            E.append(f"{r[0]}: fecha absoluta; usa TODAY±N")

    orden = section(text, "6.")
    if not orden.strip():
        E.append("Falta '## 6. Orden de construcción'")
    else:
        en_orden = set(ID("CMP").findall(orden)) | set(ID("DAT").findall(orden))
        en_orden |= set(ID("EXP").findall(orden))
        for x in sorted(set(cmp_ids) | {r[0] for r in dat}):
            if x not in en_orden:
                E.append(f"{x} no aparece en el orden de construcción")
        for x in sorted(exp_ids):
            if x not in en_orden:
                W.append(f"{x}: el paso no aparece explícitamente en el orden de construcción")

    total = sum(resp.values()) or 1
    hdr = re.search(r"\*\*Reparto:\*\*\s*IA (\d+).*?IA\+Revisión (\d+).*?Persona (\d+)", text)
    if hdr and tuple(map(int, hdr.groups())) != (resp["IA"], resp["IA+Revisión"], resp["Persona"]):
        W.append(f"Cabecera 'Reparto' no cuadra con la tabla: IA {resp['IA']} · IA+Revisión {resp['IA+Revisión']} · Persona {resp['Persona']}")
    if lvl["🟠"] / total > 0.10:
        W.append(f"{lvl['🟠']} componentes 🟠 ({lvl['🟠'] * 100 // total}%): más del 10% custom; revisa si es imprescindible para probar la hipótesis")
    if not section(text, "7.").strip():
        W.append("Falta '## 7. Supuestos y preguntas abiertas'")

    print(f"Estado: {estado} · Necesidades {len(nec)} · Hipótesis {len(hip)} · Pasos {len(exp)} · "
          f"Componentes {len(cmp_rows)} · IA {resp['IA']} ({resp['IA'] * 100 // total}%) · "
          f"IA+Revisión {resp['IA+Revisión']} · Persona {resp['Persona']} · "
          f"🟢 {lvl['🟢']} · 🔵 {lvl['🔵']} · 🟠 {lvl['🟠']}")
    for w in W:
        print("AVISO  ", w)
    for e in E:
        print("ERROR  ", e)
    print("OK" if not E else f"{len(E)} error(es)")
    return 1 if E else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0], "--gate" in sys.argv))
