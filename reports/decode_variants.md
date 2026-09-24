# Decode variants — does a commit rule fix the diffusion arm's Urdu?

See `scripts/decode_variants.py` for what each row is and what it cost.

```
decoder            temp   fwd     ooo    n   echo     d1  lrep  script  words
-----------------------------------------------------------------------------
ar                  0.7  29.6      0%  163    18%  0.852   1.9   0.996   25.9
ar                  0.8  29.7      0%  167    24%  0.868   1.4   0.999   26.4
ar                  0.9  29.8      0%  186    21%  0.893   1.2   1.000   25.8
ar                  1.0  29.4      0%  191    14%  0.907   1.1   0.993   25.2
block4/gumbel       0.7  15.2     29%  181    57%  0.567   5.0   1.000   27.2
block4/gumbel       0.8  15.2     22%  200    48%  0.619   4.2   1.000   27.0
block4/gumbel       0.9  15.2     26%  232    36%  0.711   2.8   1.000   25.8
block4/gumbel       1.0  15.2     29%  278    35%  0.763   2.4   1.000   24.8
block4/random       0.7  15.2     34%  250    44%  0.683   3.0   0.998   25.7
block4/random       0.8  15.2     38%  250    39%  0.728   2.5   1.000   25.5
block4/random       0.9  15.2     40%  280    30%  0.826   1.7   1.000   24.2
block4/random       1.0  15.2     42%  303    20%  0.861   1.4   0.998   23.2
block8/gumbel       0.7   8.0     25%  180    48%  0.580   3.3   1.000   27.0
block8/gumbel       0.8   8.0     29%  211    46%  0.639   2.6   1.000   27.0
block8/gumbel       0.9   8.0     28%  227    32%  0.689   2.4   0.999   26.5
block8/gumbel       1.0   8.0     30%  266    25%  0.789   1.7   0.998   25.4
block8/random       0.7   8.0     34%  213    36%  0.697   2.1   1.000   26.7
block8/random       0.8   8.0     34%  283    26%  0.787   1.7   0.999   25.4
block8/random       0.9   8.0     40%  280    21%  0.846   1.4   1.000   25.0
block8/random       1.0   8.0     36%  300    14%  0.887   1.2   1.000   25.0
parallel/gumbel     0.7   8.0     58%  154    69%  0.566   4.3   1.000   27.8
parallel/gumbel     0.8   8.0     54%  116    78%  0.606   4.1   1.000   28.3
parallel/gumbel     0.9   8.0     53%  158    65%  0.653   3.3   1.000   27.7
parallel/gumbel     1.0   8.0     47%  172    60%  0.694   2.8   1.000   27.3
parallel/random     0.7   8.0     56%  175    54%  0.749   2.3   1.000   27.2
parallel/random     0.8   8.0     64%  200    40%  0.789   2.0   0.999   26.5
parallel/random     0.9   8.0     65%  213    34%  0.833   1.6   0.998   25.9
parallel/random     1.0   8.0     65%  240    28%  0.877   1.3   0.998   25.2
wordwise/gumbel     0.7   8.1      0%   59    71%  0.530   4.8   1.000   29.6
wordwise/gumbel     0.8   8.1      0%   45    80%  0.580   4.3   1.000   29.8
wordwise/gumbel     0.9   8.1      0%   67    69%  0.634   3.5   1.000   29.5
wordwise/gumbel     1.0   8.1      0%   63    74%  0.663   3.2   1.000   29.5
wordwise/random     0.7   8.1      0%   68    52%  0.690   2.7   1.000   29.4
wordwise/random     0.8   8.1      0%   86    50%  0.757   2.4   0.999   29.2
wordwise/random     0.9   8.1      0%  105    38%  0.805   1.8   1.000   28.8
wordwise/random     1.0   8.1      0%  103    29%  0.844   1.6   0.999   28.9
```
