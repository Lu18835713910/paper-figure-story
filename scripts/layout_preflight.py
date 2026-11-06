"""Joint graph-card sizing and deterministic text-slot preflight using deck fonts."""
from presentation_typography import wrap,measure
def text_height(text,width_inches,size,bold=False):
    if not text:return .03
    return len(wrap(str(text),width_inches*72,size,bold).split('\n'))*size*1.34/72+.045
def card_stack(title,detail,figure,width,height,detail_min=0):
    th=max(.25,text_height(title,width-.30,12.5 if width>2 else 11,True))
    dh=max(float(detail_min or 0),text_height(detail,width-.30,10.2 if width>2 else 9.3))
    fh=text_height(figure,width-.30,8) if figure else 0
    total=.13+th+.035+dh+(.06+fh if figure else 0)+.07
    if total>height+.005:raise ValueError(f'CARD_STACK_OVERFLOW: need {total:.3f}in, have {height:.3f}; use complete B canvas and zooms; do not shrink science text')
    return dict(title_y=.13,title_h=th,detail_y=.13+th+.035,detail_h=dh,figure_y=.13+th+.035+dh+.06,figure_h=fh)
def preflight_prs(prs):
    errors=[]
    for i,slide in enumerate(prs.slides,1):
        for s in slide.shapes:
            if not s.has_text_frame or not s.text.strip():continue
            if s.name not in ['PFS_LEAD','PFS_TRANSITION','PFS_RESULT','PFS_GRAPH_NODE_TITLE','PFS_GRAPH_NODE_DETAIL','PFS_GRAPH_FIGREF','PFS_EDGE_LABEL']:continue
            tf=s.text_frame;sizes=[r.font.size.pt for p in tf.paragraphs for r in p.runs if r.font.size];size=max(sizes or [10])
            width=(s.width-tf.margin_left-tf.margin_right)/914400
            try:
                lines=wrap(s.text,width*72,size,s.name=='PFS_GRAPH_NODE_TITLE').split('\n')
                if max(measure(line,size,s.name=='PFS_GRAPH_NODE_TITLE') for line in lines)>width*72+.1:
                    errors.append(dict(slide=i,shape=s.name,code='SLOT_WIDTH_CAPACITY'))
            except ValueError as e:
                errors.append(dict(slide=i,shape=s.name,code='TEXT_ATOM_CAPACITY',detail=str(e)));continue
            try:need=text_height(s.text,width,size,s.name=='PFS_GRAPH_NODE_TITLE')
            except ValueError as e:errors.append(dict(slide=i,shape=s.name,code='TEXT_ATOM_CAPACITY',detail=str(e)));continue
            have=(s.height-tf.margin_top-tf.margin_bottom)/914400
            if need>have+.035:errors.append(dict(slide=i,shape=s.name,code='SLOT_CAPACITY',needed=need,available=have))
    return dict(valid=not errors,errors=errors,basis='Actual installed mixed-script fonts when available; conservative fallback otherwise. Does not replace actual Office geometry or visual review.')

