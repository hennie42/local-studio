"""Tiny draw.io (mxGraph XML) writer: boxes, edges, lanes. Colours = roles, dashed = planned."""
from xml.sax.saxutils import escape

C = {  # fill, stroke
    "you": ("#fff2cc", "#d6b656"), "claude": ("#dae8fc", "#6c8ebf"), "local": ("#d5e8d4", "#82b366"),
    "broker": ("#e1d5e7", "#9673a6"), "check": ("#f8cecc", "#b85450"), "file": ("#f5f5f5", "#666666"),
    "gpu": ("#ffe6cc", "#d79b00"), "plain": ("#ffffff", "#666666"),
}


class D:
    def __init__(self, name, w=1200, h=800):
        self.name, self.w, self.h, self.cells, self.n = name, w, h, [], 0

    def _id(self, i=None):
        self.n += 1
        return i or f"c{self.n}"

    def box(self, x, y, w, h, label, role="plain", id=None, shape="rounded=1;arcSize=12;", extra="", planned=False,
            fs=13, parent="1"):
        f, s = C[role]
        st = (f"{shape}whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};fontSize={fs};fontFamily=Helvetica;"
              f"{'dashed=1;dashPattern=6 4;' if planned else ''}{extra}")
        id = self._id(id)
        self.cells.append(f'<mxCell id="{id}" value="{escape(label, {chr(34): "&quot;"})}" style="{st}" vertex="1" '
                          f'parent="{parent}"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return id

    def doc(self, *a, **k):
        return self.box(*a, shape="shape=note;size=14;", **k)

    def actor(self, x, y, label, id=None):
        f, s = C["you"]
        id = self._id(id)
        self.cells.append(f'<mxCell id="{id}" value="{escape(label)}" style="shape=umlActor;verticalLabelPosition=bottom;'
                          f'verticalAlign=top;html=1;fillColor={f};strokeColor={s};fontSize=14;fontStyle=1;" vertex="1" '
                          f'parent="1"><mxGeometry x="{x}" y="{y}" width="40" height="70" as="geometry"/></mxCell>')
        return id

    def text(self, x, y, w, h, label, fs=13, extra="align=left;verticalAlign=top;"):
        id = self._id()
        self.cells.append(f'<mxCell id="{id}" value="{escape(label, {chr(34): "&quot;"})}" style="text;html=1;'
                          f'whiteSpace=wrap;fontSize={fs};fontFamily=Helvetica;{extra}" vertex="1" parent="1">'
                          f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        return id

    def edge(self, src, tgt, label="", dashed=False, color="#333333", extra="", pts=None, both=False,
             exit=None, entry=None):
        st = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endFill=1;strokeColor={color};"
              f"strokeWidth=1.5;fontSize=12;fontFamily=Helvetica;labelBackgroundColor=#ffffff;"
              f"{'dashed=1;' if dashed else ''}{'startArrow=block;startFill=1;' if both else ''}{extra}")
        if exit:
            st += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            st += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        p = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in (pts or []))
        p = f'<Array as="points">{p}</Array>' if p else ""
        self.cells.append(f'<mxCell id="{self._id()}" value="{escape(label, {chr(34): "&quot;"})}" style="{st}" edge="1" '
                          f'parent="1" source="{src}" target="{tgt}"><mxGeometry relative="1" as="geometry">{p}'
                          f'</mxGeometry></mxCell>')

    def arrow(self, x1, y1, x2, y2, label="", dashed=False, color="#333333", extra=""):
        """Free arrow between points (sequence diagrams)."""
        st = (f"html=1;endArrow=block;endFill=1;strokeColor={color};strokeWidth=1.5;fontSize=12;fontFamily=Helvetica;"
              f"labelBackgroundColor=#ffffff;verticalAlign=bottom;{'dashed=1;' if dashed else ''}{extra}")
        self.cells.append(f'<mxCell id="{self._id()}" value="{escape(label, {chr(34): "&quot;"})}" style="{st}" edge="1" '
                          f'parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
                          f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/></mxGeometry></mxCell>')

    def line(self, x1, y1, x2, y2, color="#999999"):
        self.cells.append(f'<mxCell id="{self._id()}" style="endArrow=none;html=1;dashed=1;strokeColor={color};" edge="1" '
                          f'parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
                          f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/></mxGeometry></mxCell>')

    def legend(self, x, y, items, per_row=4, step=190):
        self.text(x, y, 200, 20, "<b>Legend</b>", fs=12)
        for i, (role, label, planned) in enumerate(items):
            self.box(x + (i % per_row) * step, y + 24 + (i // per_row) * 32, 22, 18, "", role, planned=planned)
            self.text(x + 28 + (i % per_row) * step, y + 22 + (i // per_row) * 32, step - 30, 22, label, fs=12)

    def xml(self):
        body = "".join(self.cells)
        return (f'<mxfile host="drawio"><diagram id="{self.name}" name="{self.name}"><mxGraphModel dx="1200" dy="800" '
                f'grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{self.w}" pageHeight="{self.h}" background="#ffffff" math="0" shadow="0"><root>'
                f'<mxCell id="0"/><mxCell id="1" parent="0"/>{body}</root></mxGraphModel></diagram></mxfile>\n')
