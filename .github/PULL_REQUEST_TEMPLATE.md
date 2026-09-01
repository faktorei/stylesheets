<!--
Thanks for contributing. The most valuable PR here is a fixture that breaks a
renderer — see CONTRIBUTING.md.

Note the flow is asymmetric and we state it plainly: this repo is a one-way
mirror of the Apache-2.0 subset of a private monorepo, where the full gate stack
runs. A maintainer applies your change upstream, and it returns in the next sync.
Your PR is then closed with a reference to that sync commit. Your authorship is
preserved in the upstream commit trailer.
-->

## What this changes

<!-- One or two sentences. If it is a fixture, say what it renders wrong today. -->

## Expected vs. actual

<!-- For a rendering or validation change, what should happen and what does. -->

## Checks run

<!-- Tick what you ran. Not all of them apply to every change, and you do NOT
     need to bless visual baselines — those live in the monorepo. -->

- [ ] `python3 specwatch/pull.py` — vendored the pinned official artefacts
- [ ] `python3 tools/validate.py --all` — 0 fatal / 0 warning
- [ ] `python3 tools/render.py <fixture> out.pdf` — produces a PDF
- [ ] `python3 tools/test_equivalence.py` — UBL/CII twins still identical
- [ ] `python3 tools/test_money.py` — number formatting unchanged
- [ ] `python3 tools/test_profile.py` — profile deltas still scoped
- [ ] New fixture is registered in `corpus/manifest.yaml` with its `profile`
- [ ] Sample data is anonymised (fictional parties, addresses, tax IDs)

## Contributor License Agreement

- [ ] **I have read [CLA.md](../CLA.md) and I agree to it for this and my future
      contributions to the Project.**

<!--
The CLA is lightweight and Apache-style: it grants a copyright and patent licence
so the project can stay Apache-2.0 and relicense-safe. It does not assign
ownership, and it does not change the licence of the project itself.
-->
