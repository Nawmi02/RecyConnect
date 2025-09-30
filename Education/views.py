from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import FileResponse, Http404
from django.db.models import F, Q
from django.utils.encoding import smart_str
import mimetypes

from .models import Learn, Tag


def _get_int(value, default=1, min_value=None, max_value=None):
    try:
        v = int(value)
    except (TypeError, ValueError):
        v = default
    if min_value is not None and v < min_value:
        v = min_value
    if max_value is not None and v > max_value:
        v = max_value
    return v

from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import render

def _education_awareness_common(request, template_name):
    tab = (request.GET.get("tab") or "guides").strip().lower()
    tag_code = request.GET.get("tag")
    q = (request.GET.get("q") or "").strip()

    if tab == "videos":
        qs = Learn.objects.filter(category=Learn.Category.VIDEO)
    elif tab == "tips":
        qs = Learn.objects.filter(category=Learn.Category.QUICK_TEXT)
    else:
        qs = Learn.objects.filter(category__in=[Learn.Category.GUIDELINE, Learn.Category.ARTICLE])

    if tag_code:
        qs = qs.filter(
            Q(tags__name__iexact=tag_code) |
            Q(tags__code__iexact=tag_code) |
            Q(tags__slug__iexact=tag_code)
        )

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(topic__icontains=q) |
            Q(description__icontains=q) |
            Q(quick_text__icontains=q)
        )

    qs = qs.prefetch_related("tags").order_by("-created_at")

    page_number = _get_int(request.GET.get("page"), default=1, min_value=1)
    paginator = Paginator(qs, 6)
    try:
        page_obj = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    context = {
        "active_tab": "videos" if tab == "videos" else ("tips" if tab == "tips" else "guides"),
        "items": page_obj,
        "page_obj": page_obj,
        "cat_choices": Learn.Category.choices,
        "tag_choices": Tag.Choices.choices,
        "selected_tag": tag_code,
        "query": q,
    }
    return render(request, template_name, context)

def education_awareness_h(request):
    return _education_awareness_common(request, "Household/h_learn.html")

def education_awareness_c(request):
    return _education_awareness_common(request, "Collector/c_learn.html")

def education_awareness_b(request):
    return _education_awareness_common(request, "Buyer/b_learn.html")




# ---------- Guides/Articles ----------
def view_guide_pdf(request, pk):
    guide = get_object_or_404(Learn, pk=pk, category__in=[Learn.Category.GUIDELINE, Learn.Category.ARTICLE])
    if not guide.pdf_file:
        raise Http404("PDF not found")

    filename = guide.pdf_file.name.split("/")[-1]
    resp = FileResponse(guide.pdf_file.open("rb"), content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="{smart_str(filename)}"'
    return resp


def download_guide_pdf(request, pk):
    guide = get_object_or_404(Learn, pk=pk, category__in=[Learn.Category.GUIDELINE, Learn.Category.ARTICLE])
    if not guide.pdf_file:
        raise Http404("PDF not found")

    Learn.objects.filter(pk=pk).update(downloads=F("downloads") + 1)

    filename = guide.pdf_file.name.split("/")[-1]
    return FileResponse(guide.pdf_file.open("rb"), as_attachment=True, filename=filename)


# ---------- Videos ----------
def view_video(request, pk):
    video = get_object_or_404(Learn, pk=pk, category=Learn.Category.VIDEO)
    if not video.video_file:
        raise Http404("Video not found")

    filename = video.video_file.name.split("/")[-1]
    ctype, _ = mimetypes.guess_type(filename)
    resp = FileResponse(video.video_file.open("rb"), content_type=ctype or "video/mp4")
    resp["Content-Disposition"] = f'inline; filename="{smart_str(filename)}"'
    return resp


def download_video(request, pk):
    video = get_object_or_404(Learn, pk=pk, category=Learn.Category.VIDEO)
    if not video.video_file:
        raise Http404("Video not found")

    Learn.objects.filter(pk=pk).update(downloads=F("downloads") + 1)

    filename = video.video_file.name.split("/")[-1]
    ctype, _ = mimetypes.guess_type(filename)
    resp = FileResponse(video.video_file.open("rb"), content_type=ctype or "application/octet-stream")
    resp["Content-Disposition"] = f'attachment; filename="{smart_str(filename)}"'
    return resp
