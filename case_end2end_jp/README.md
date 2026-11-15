# Second end-to-end case: Japan → Singapore individual

Fictitious. Chosen on 2026-11-12 from the savings map (`optimization/tools/savings_map.py`): a Japanese company paying its
Singapore-resident individual owner bears 15% Japanese withholding under the treaty; held through a Singapore company that has
held at least 25% for six months, the treaty rate is 5%, and Singapore exempts the dividend in the company's hands (s13(8)) and
in the individual's (one-tier). The case exercises what the first case could not:

- a real saving per payment (about JPY 20 million on a JPY 200 million dividend) against a one-off cost that can be computed
  (net assets and the cost of the shares are given), so a payback in payments;
- the order of this payment and later payments: the December dividend cannot wait for the new holder's holding period, so it is
  paid as things stand and the transfer serves later dividends (`sequence.json`);
- the client's own conduct, stated: the money must reach Singapore, this payment cannot wait, it is not yet declared.

`prompt.md` is the client's background (entered as text; no documents). `facts.json` is the ground truth the simulated client
answers from; anything not in it is answered "I cannot say".
