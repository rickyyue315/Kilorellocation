"""
Mojibake 修復模組 — 修復 Streamlit 文字渲染中的亂碼問題
"""

try:
    from streamlit.delta_generator import DeltaGenerator
except Exception:
    DeltaGenerator = None

try:
    import ftfy
except Exception:
    ftfy = None


def fix_mojibake_text(value):
    if not isinstance(value, str) or not value:
        return value
    if ftfy is None:
        return value
    try:
        return ftfy.fix_text(value)
    except Exception:
        return value


def fix_mojibake_value(value):
    if isinstance(value, str):
        return fix_mojibake_text(value)
    if isinstance(value, list):
        return [fix_mojibake_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(fix_mojibake_value(item) for item in value)
    return value


def patch_streamlit_text_rendering():
    if DeltaGenerator is None or ftfy is None:
        return

    patch_rules = {
        'markdown': {'arg_indexes': [0], 'kw_keys': []},
        'title': {'arg_indexes': [0], 'kw_keys': []},
        'header': {'arg_indexes': [0], 'kw_keys': []},
        'subheader': {'arg_indexes': [0], 'kw_keys': []},
        'text': {'arg_indexes': [0], 'kw_keys': []},
        'caption': {'arg_indexes': [0], 'kw_keys': []},
        'code': {'arg_indexes': [0], 'kw_keys': []},
        'info': {'arg_indexes': [0], 'kw_keys': []},
        'warning': {'arg_indexes': [0], 'kw_keys': []},
        'error': {'arg_indexes': [0], 'kw_keys': []},
        'success': {'arg_indexes': [0], 'kw_keys': []},
        'button': {'arg_indexes': [0], 'kw_keys': []},
        'download_button': {'arg_indexes': [0], 'kw_keys': []},
        'file_uploader': {'arg_indexes': [0], 'kw_keys': []},
        'checkbox': {'arg_indexes': [0], 'kw_keys': []},
        'radio': {'arg_indexes': [0, 1], 'kw_keys': ['options']},
        'selectbox': {'arg_indexes': [0, 1], 'kw_keys': ['options']},
        'multiselect': {'arg_indexes': [0, 1], 'kw_keys': ['options']},
        'tabs': {'arg_indexes': [0], 'kw_keys': []},
        'expander': {'arg_indexes': [0], 'kw_keys': []},
        'metric': {'arg_indexes': [0, 2], 'kw_keys': ['label', 'delta']}
    }

    def make_wrapper(method_name, original, arg_indexes, kw_keys):
        def wrapper(self, *args, **kwargs):
            args = list(args)

            if method_name == 'write':
                args = [fix_mojibake_value(arg) for arg in args]
            else:
                for index in arg_indexes:
                    if index < len(args):
                        args[index] = fix_mojibake_value(args[index])

            for key in kw_keys:
                if key in kwargs:
                    kwargs[key] = fix_mojibake_value(kwargs[key])

            return original(self, *args, **kwargs)

        wrapper._kilo_mojibake_patched = True
        return wrapper

    write_original = getattr(DeltaGenerator, 'write', None)
    if write_original is not None and not getattr(write_original, '_kilo_mojibake_patched', False):
        setattr(DeltaGenerator, 'write', make_wrapper('write', write_original, [], []))

    for method_name, rule in patch_rules.items():
        original = getattr(DeltaGenerator, method_name, None)
        if original is None or getattr(original, '_kilo_mojibake_patched', False):
            continue
        wrapped = make_wrapper(method_name, original, rule['arg_indexes'], rule['kw_keys'])
        setattr(DeltaGenerator, method_name, wrapped)
