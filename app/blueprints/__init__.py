################################################################################
# Utility to print everything coming back from HTMX request from client HTML:
################################################################################
def hx_debug(request) -> None:
    print("Headers:")
    for header, value in request.headers:
        print(f"{header}: {value}")

    print("\nQuery Parameters:")
    for key, value in request.args.items():
        print(f"{key}: {value}")

    print("\nPOST Parameters:")
    for key, value in request.form.items():
        print(f"{key}: {value}")

    print("\nHX-specific headers:")
    hx_headers = {k: v for k, v in request.headers if k.startswith("Hx-")}
    for header, value in hx_headers.items():
        print(f"{header}: {value}")
