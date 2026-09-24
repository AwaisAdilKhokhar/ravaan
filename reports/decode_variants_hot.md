# Decode variants — does a commit rule fix the diffusion arm's Urdu?

See `scripts/decode_variants.py` for what each row is and what it cost.

```
decoder            temp   fwd     ooo    n   echo     d1  lrep  script  words
-----------------------------------------------------------------------------
ar                  1.1  29.4      0%  253     9%  0.927   0.9   0.990   24.4
ar                  1.2  29.0      0%  250     2%  0.949   0.7   0.990   23.6
ar                  1.3  29.1      0%  282     6%  0.955   0.7   0.966   23.3
block8/gumbel       1.1   8.0     31%  309    24%  0.870   1.3   1.000   24.2
block8/gumbel       1.2   8.0     31%  326    11%  0.901   1.0   0.994   24.0
block8/gumbel       1.3   8.0     36%  355    10%  0.932   0.8   0.988   23.3
block8/random       1.1   8.0     37%  332    11%  0.919   1.0   0.999   23.8
block8/random       1.2   8.0     34%  367     5%  0.955   0.7   0.998   23.6
block8/random       1.3   8.0     33%  368     5%  0.964   0.7   0.986   23.5
parallel/gumbel     1.1   8.0     58%  182    46%  0.724   2.9   0.999   27.2
parallel/gumbel     1.2   8.0     64%  190    40%  0.787   2.1   0.995   26.9
parallel/gumbel     1.3   8.0     56%  231    29%  0.850   1.5   0.993   25.6
parallel/random     1.1   8.0     60%  280    12%  0.910   1.1   0.996   24.3
parallel/random     1.2   8.0     59%  305     6%  0.932   0.9   0.989   24.2
parallel/random     1.3   8.0     58%  334     5%  0.950   0.7   0.981   23.1
wordwise/gumbel     1.1   8.2      0%   74    51%  0.728   2.7   0.999   29.3
wordwise/gumbel     1.2   8.2      0%   90    49%  0.766   2.4   0.997   29.1
wordwise/gumbel     1.3   8.2      0%  112    41%  0.827   1.9   0.996   28.7
wordwise/random     1.1   8.1      0%  124    15%  0.875   1.3   0.997   28.6
wordwise/random     1.2   8.1      0%  118    14%  0.902   1.2   0.991   28.7
wordwise/random     1.3   8.1      0%  163     6%  0.928   0.9   0.985   28.1
```
