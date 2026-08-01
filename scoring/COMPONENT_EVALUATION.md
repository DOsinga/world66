# Component Evaluation

This is a sanity check of the current component scores in `scoring/data/location_scores.json`.

The combined `score` is not treated as a quality ranking here. It is a compatibility regression against the old frontmatter `score`, and the Bergen result shows that it should not be used as "best places to visit" without further calibration.

## Verdict

The four component signals are useful for broad filtering and candidate generation. They are not reliable enough for final visible top lists without a runoff or human steering layer.

- `heritage` is the strongest component. The top tail is mostly real heritage-heavy destinations.
- `nature` is usable and separates well from easy, managed places.
- `off_the_beaten_track` is much better than the old `adventure` label, but still over-rewards remote islands in some cases.
- `vibrancy` is the weakest component for top ordering. It works as a broad lively-city flag, but it over-scores some places and under-scores several obvious global city destinations.

## Correlations

Current model prediction correlations over all scored locations:

| Pair | Correlation |
|---|---:|
| `heritage` / `vibrancy` | `0.440` |
| `nature` / `off_the_beaten_track` | `0.559` |

The nature/offbeat split is no longer collapsed, but it is still meaningfully coupled.

## Known City Checks

| Place | Heritage | Vibrancy | Nature | Offbeat | Notes |
|---|---:|---:|---:|---:|---|
| Paris | `8.8` | `7.8` | `4.5` | `2.2` | Strong heritage, vibrancy lower than expected. |
| New York | `7.8` | `8.5` | `4.8` | `2.1` | Vibrancy looks right; heritage plausible. |
| Tokyo | `8.2` | `8.7` | `5.0` | `2.4` | Good vibrancy result. |
| London | `8.1` | `8.1` | `5.7` | `1.3` | Broadly plausible. |
| Bangkok | `7.3` | `8.6` | `4.5` | `3.2` | Vibrancy looks right. |
| Istanbul | `8.3` | `8.5` | `5.6` | `2.3` | Strong result. |
| Rome | `8.5` | `6.8` | `3.6` | `1.9` | Vibrancy too low. |
| Barcelona | `8.2` | `7.5` | `5.1` | `1.6` | Vibrancy low for this class of city. |
| Amsterdam | `8.0` | `7.4` | `3.7` | `1.1` | Vibrancy low. |
| Dubai | `6.5` | `8.1` | `5.1` | `1.8` | Plausible urban/refined vibrancy. |
| Bergen | `8.0` | `7.5` | `8.8` | `3.1` | Component scores are plausible; combined score is not. |
| Baghdad | `8.4` | `7.2` | `2.7` | `3.3` | Heritage plausible; vibrancy may be high for visitor-accessible vibrancy. |
| Mosul | `7.6` | `5.4` | `3.5` | `4.2` | More plausible than earlier runs. |
| Lagos | `6.5` | `8.4` | `4.3` | `2.5` | Vibrancy plausible. |
| Damascus | `8.4` | `7.0` | `2.5` | `3.5` | Heritage plausible; vibrancy/offbeat debatable. |

## Nature And Offbeat Checks

High nature with low or moderate offbeat now looks much better:

| Place | Nature | Offbeat |
|---|---:|---:|
| Lake Louise | `9.0` | `3.9` |
| Plitvice | `8.9` | `3.3` |
| Rotorua | `8.8` | `2.8` |
| Mount Fuji | `8.6` | `3.2` |
| Iguazu Falls | `8.2` | `2.8` |
| Maui | `8.1` | `2.6` |
| Sorrento | `8.3` | `2.2` |
| Hakone | `8.5` | `2.6` |
| Honolulu | `7.7` | `2.1` |

High offbeat also mostly finds hard, remote, or less-managed places:

| Place | Nature | Offbeat |
|---|---:|---:|
| Trans Sahara | `7.1` | `8.9` |
| Gobi Desert | `8.7` | `8.9` |
| Qaanaaq | `8.0` | `8.8` |
| Socotra | `8.2` | `8.7` |
| Danakil Depression | `8.2` | `8.7` |
| Timbuktu | `3.7` | `8.4` |

The main offbeat concern is remote island inflation. Aitutaki, Koror, Rock Islands, and Funafuti score very high on offbeat, and those may need runoff review before appearing in visible top lists.

## Top Tail Concerns

`heritage` top results are mostly plausible: Ephesus, Ellora, Petra, Cuzco, Cairo, Varanasi, Borobudur, Jerash, and similar places score very high.

`vibrancy` top ordering is less reliable. Tokyo, Istanbul, New York, Bangkok, Mexico City, Beijing, and Lagos are strong, but places such as Kigali, Kampala, Brasilia, and Pyongyang appear too high relative to globally obvious visitor-vibrancy places. Rome, Barcelona, Amsterdam, Montreal, Chicago, and Dakar look low.

## Product Use

Use the components for:

- broad filters;
- candidate generation;
- map exploration;
- personalization inputs;
- picking runoff candidates.

Do not use the raw component order as final editorial ranking for top city lists. Do not use the combined `score` as a general "best places" ranking.
