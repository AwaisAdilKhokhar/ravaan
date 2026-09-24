# Decode variants — does a commit rule fix the diffusion arm's Urdu?

See `scripts/decode_variants.py` for what each row is and what it cost.

```
decoder            temp   fwd   bad   inv chars   ooo  tied    n  echo     d1  lrep  words
------------------------------------------------------------------------------------------
ar                  0.8  29.7   10%  0.1%  3.35    0%    0%  167   24%  0.868   1.4   26.4
ar                  1.0  29.4   15%  0.6%  3.50    0%    0%  191   14%  0.907   1.1   25.2
block8/gumbel 2     0.8   8.0   38%  1.5%  3.20   29%   37%  211   46%  0.639   2.6   27.0
block8/gumbel 2     1.0   8.0   65%  5.0%  3.42   30%   40%  266   25%  0.789   1.7   25.4
block8/random       0.8   8.0   64%  4.1%  3.35   34%   36%  283   26%  0.787   1.7   25.4
block8/random       1.0   8.0   84%  5.4%  3.55   36%   34%  300   14%  0.887   1.2   25.0
parallel/gumbel 2   0.8   8.0    6%  0.2%  3.32   54%   13%  116   78%  0.606   4.1   28.3
parallel/gumbel 2   1.0   8.0   14%  0.6%  3.33   47%   14%  172   60%  0.694   2.8   27.3
parallel/random     0.8   8.0   24%  1.2%  3.37   64%    7%  200   40%  0.789   2.0   26.5
parallel/random     1.0   8.0   46%  2.5%  3.50   65%    7%  240   28%  0.877   1.3   25.2
wordwise/gumbel 2   0.8   8.1    1%  0.0%  3.29    0%    0%   45   80%  0.580   4.3   29.8
wordwise/gumbel 2   1.0   8.1    5%  0.0%  3.29    0%    0%   63   74%  0.663   3.2   29.5
wordwise/random     0.8   8.1    6%  0.0%  3.30    0%    0%   86   50%  0.757   2.4   29.2
wordwise/random     1.0   8.1   15%  0.2%  3.41    0%    0%  103   29%  0.844   1.6   28.9
```
