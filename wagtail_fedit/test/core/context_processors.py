def test_context_processor(request):
    return {
        "fedit": True,
        "testing": "testing context processor",
    }