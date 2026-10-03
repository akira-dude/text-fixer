from textfixer.layout import fix_layout

CASES = [
    ("ghbdtn rfr ltkf", "привет как дела"),
    ("Ghbdtn? rfr ltkf&", "Привет, как дела?"),
    ("z nt,z k.,k.", "я тебя люблю"),
    ("lf", "да"),
    ("jr", "ок"),
    ("ntcn", "тест"),
    ("ktn yt dbltkb", "лет не видели"),
    ("vs gjcvjnhbv xnj nfv c cthdthjv", "мы посмотрим что там с сервером"),
    ("руддщ рщц фку нщг", "hello how are you"),
    ("Привет, ghbdtn", "Привет, привет"),
    ("hello how are you", "hello how are you"),
    ("привет как дела", "привет как дела"),
    ("ok", "ok"),
    ("lol", "lol"),
    ("xD", "xD"),
    ("gg wp", "gg wp"),
    ("npm install", "npm install"),
    ("git push origin main", "git push origin main"),
    ("смотри https://github.com/foo", "смотри https://github.com/foo"),
    ("ckjdj https://github.com/foo", "слово https://github.com/foo"),
    ("@user ghbdtn", "@user привет"),
    ("ыщккн", "sorry"),
    ("ну ок, давай завтра", "ну ок, давай завтра"),
    ("Я написал код, он работает.", "Я написал код, он работает."),
    ("I wrote the code, it works.", "I wrote the code, it works."),
    ("Z yfgbcfk rjl? jy hf,jnftn/", "Я написал код, он работает."),
    ("  ghbdtn\n", "  привет\n"),
]

def main():
    fails = 0
    for src, want in CASES:
        got = fix_layout(src)
        ok = got == want
        fails += not ok
        print(("OK  " if ok else "FAIL"), repr(src), "->", repr(got), "" if ok else f"(want {want!r})")
    print(f"{len(CASES) - fails}/{len(CASES)} passed")
    return fails

if __name__ == "__main__":
    raise SystemExit(main())
