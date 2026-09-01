# Les concepts de la page /roadmap, de zéro à l'aisance

La page `/roadmap` liste dix-sept chantiers, dont neuf sont des chantiers de
**modélisation**. Chacun s'appuie sur un objet mathématique que la page se
contente de nommer. Ce document explique ces objets.

Le format est le même partout : **définition**, puis **intuition**, puis **les
maths**, puis **un exemple chiffré à la main** sur des données assez petites
pour être vérifiées de tête ou à la calculatrice, puis **ce que ça change ici**.

Tous les chiffres de ce document ont été calculés, pas recopiés. Les valeurs du
projet (λ = 0,3052, μ = 12,1186, AAL = 273 704 €…) viennent du moteur ; les
exemples jouets sont calculés à part et reproduits tels quels.

**Prérequis** : probabilités et statistique de niveau licence — variable
aléatoire, espérance, variance, densité, fonction de répartition, maximum de
vraisemblance. Rien de plus.

---

## Table des matières

**Partie I — le socle** (à lire avant le reste)
1. [Processus de Poisson et taux λ](#1-processus-de-poisson-et-taux-λ)
2. [Loi lognormale](#2-loi-lognormale)
3. [Loi composée et pourquoi Monte Carlo](#3-loi-composée-et-pourquoi-monte-carlo)
4. [AAL, VaR, TVaR](#4-aal-var-tvar)
5. [Pondération douce et taille d'échantillon effective de Kish](#5-pondération-douce-et-taille-déchantillon-effective-de-kish)
6. [Statistique de Kolmogorov–Smirnov](#6-statistique-de-kolmogorovsmirnov)

**Partie II — les neuf chantiers de modélisation**

7. [Sensibilité et élasticité](#7-sensibilité-et-élasticité) → *Report the answer's sensitivity to p_materialize*
8. [Backtesting : CRPS, PIT, validation croisée](#8-backtesting--crps-pit-validation-croisée) → *Backtest against the incident base*
9. [Crédibilité Gamma-Poisson](#9-crédibilité-gamma-poisson) → *Gamma-Poisson credibility*
10. [Le cadre FAIR](#10-le-cadre-fair) → *Model p_materialize* et *Control effectiveness*
11. [Théorie des valeurs extrêmes : POT et GPD](#11-théorie-des-valeurs-extrêmes--pot-et-gpd) → *GPD tail*
12. [Écrêtage contre troncature](#12-écrêtage-contre-troncature) → *Derive the loss cap*
13. [Dépendance et copules](#13-dépendance-et-copules) → *Dependence between attack types*
14. [Allocation par actif](#14-allocation-par-actif) → *Asset-level loss allocation*

**Partie III**
15. [Glossaire](#15-glossaire)

---

# Partie I — le socle

## 1. Processus de Poisson et taux λ

### Définition

Un **processus de Poisson** d'intensité λ compte des événements qui arrivent
« au hasard » à un rythme moyen constant. Le nombre d'événements N observés sur
une durée d'un an suit la **loi de Poisson** de paramètre λ :

$$P(N = k) = \frac{\lambda^k e^{-\lambda}}{k!}, \qquad k = 0, 1, 2, \dots$$

avec E[N] = Var(N) = λ.

### Intuition

λ n'est pas « le nombre d'incidents par an ». C'est le **rythme moyen**. Une
entreprise avec λ = 0,31 ne subit pas « 0,31 incident » — elle en subit zéro la
plupart des années, un parfois, deux très rarement. C'est le seul modèle qui
respecte trois propriétés qu'on veut ici :

- les événements sont **entiers** (on ne subit pas un tiers d'incident) ;
- ils sont **indépendants** dans le temps ;
- le rythme est **constant** — c'est précisément ce que la platitude du débit
  hebdomadaire, sur les 212 jours observés, autorise à supposer.

### Les maths, appliquées au projet

λ = 0,3052 incident à perte par an. Donc :

| k | calcul | P(N = k) |
|---|---|---|
| 0 | e^(−0,3052) | **0,736976** |
| 1 | 0,3052 · e^(−0,3052) | 0,224925 |
| 2 | 0,3052² / 2 · e^(−0,3052) | 0,034324 |
| 3 | 0,3052³ / 6 · e^(−0,3052) | 0,003492 |

**C'est d'où vient le « 73,7 % des années sans incident » de la slide 12 et de
la page /simulation.** Ce n'est pas une sortie de simulation, c'est e^(−λ) : la
simulation le retrouve, ce qui est un contrôle de cohérence gratuit.

Et P(au moins un incident) = 1 − 0,736976 = **0,263024**, soit les 26,3 %
d'« années à perte » de l'histogramme.

### Annualisation

Le taux est estimé sur 212 jours, pas sur un an. Le facteur d'annualisation est
donc 365 / 212 = **1,7217**. Ce n'est pas une constante écrite en dur : elle est
recalculée depuis la fenêtre réellement observée, donc un export plus long
change le résultat sans toucher au code.

---

## 2. Loi lognormale

### Définition

X suit une loi **lognormale** de paramètres (μ, σ) si ln X suit une loi normale
N(μ, σ²). Densité :

$$f(x) = \frac{1}{x\sigma\sqrt{2\pi}} \exp\left(-\frac{(\ln x - \mu)^2}{2\sigma^2}\right), \quad x > 0$$

Les deux moments qui comptent :

$$\text{médiane} = e^{\mu} \qquad\qquad \mathbb{E}[X] = e^{\mu + \sigma^2/2}$$

**Attention à la notation** : μ et σ sont les paramètres de la loi normale
*sous-jacente*, sur l'échelle des logarithmes. Ce **ne sont pas** la moyenne et
l'écart-type de X. C'est la source d'erreur numéro un avec cette loi.

### Intuition

Trois raisons de choisir cette forme pour une perte :

1. **Elle est strictement positive.** Une perte ne peut pas être négative, ce
   qui exclut d'emblée la loi normale.
2. **Elle n'a pas de plafond.** Il n'existe pas de « perte maximale » naturelle.
3. **Elle est multiplicative.** Une perte se construit par facteurs qui se
   multiplient — nombre de dossiers × coût par dossier × durée d'indisponibilité
   — et un produit de facteurs positifs tend vers une lognormale par le théorème
   central limite appliqué aux logarithmes.

Empiriquement : sur les données du projet, l'asymétrie des pertes brutes vaut
7,4 ; celle des log-pertes tombe à 0,80. Le passage au log fait presque tout le
travail.

### L'écart médiane / moyenne

C'est le fait le plus important de tout le projet. Sur le type `supply_chain` :

- μ = 12,118637, σ = 2,581549
- médiane = e^12,118637 = **183 256 €**
- moyenne = e^(12,118637 + 2,581549²/2) = e^(12,118637 + 3,332197) = **5 131 124 €**

Le rapport moyenne / médiane vaut e^(σ²/2) = e^3,332197 = **28,0**.

L'incident *typique* coûte 183 k€. Le coût *moyen* est 28 fois plus élevé, parce
qu'une petite fraction d'incidents coûte des millions. Et c'est la **moyenne**,
pas la médiane, qui alimente la perte annuelle : E[perte annuelle] = λ · E[X].
Un décideur qui raisonne sur « l'incident typique » se trompe d'un facteur 28.

### Exemple chiffré : ajuster une lognormale à la main

Cinq pertes observées :

```
10 000    40 000    120 000    900 000    6 000 000
```

**Étape 1 — passer au log** (log népérien) :

```
ln(10 000)    = 9,2103
ln(40 000)    = 10,5966
ln(120 000)   = 11,6952
ln(900 000)   = 13,7102
ln(6 000 000) = 15,6073
```

**Étape 2 — le maximum de vraisemblance sur une lognormale, c'est simplement la
moyenne et l'écart-type des logs** (c'est la propriété qui rend cette loi si
commode) :

```
μ̂ = (9,2103 + 10,5966 + 11,6952 + 13,7102 + 15,6073) / 5 = 12,1639
σ̂ = √( Σ(lnxᵢ − μ̂)² / 5 ) = 2,2648
```

**Étape 3 — revenir en euros :**

```
médiane = e^12,1639           = 191 746 €
moyenne = e^(12,1639 + 2,2648²/2) = 2 492 120 €
```

**Le contrôle qui compte.** La moyenne arithmétique brute des cinq nombres vaut
1 414 000 €. Le modèle, lui, annonce 2 492 120 €, soit **76 % de plus**. Ce
n'est pas une erreur : le modèle dit que ces cinq observations proviennent d'une
loi dont la queue, encore jamais observée sur si peu de points, contribue
lourdement à l'espérance. C'est exactement le comportement souhaité pour du
risque — et exactement pourquoi il faut ensuite un plafond de plausibilité
(§12).

### Pondération

Dans le projet, l'ajustement est **pondéré** : chaque incident porte un poids wᵢ
selon sa ressemblance avec l'entreprise cible. Les formules deviennent

$$\hat\mu = \frac{\sum w_i \ln x_i}{\sum w_i} \qquad \hat\sigma^2 = \frac{\sum w_i (\ln x_i - \hat\mu)^2}{\sum w_i}$$

C'est la même chose avec des poids. Voir §5 pour ce que la pondération coûte.

---

## 3. Loi composée et pourquoi Monte Carlo

### Définition

La perte annuelle S est une **somme aléatoire d'un nombre aléatoire de termes** :

$$S = \sum_{i=1}^{N} X_i, \qquad N \sim \text{Poisson}(\lambda), \quad X_i \sim \text{Lognormale}(\mu, \sigma)$$

avec N et les Xᵢ indépendants. On appelle ça une **loi de Poisson composée**.

### Intuition

Une année n'est pas « la fréquence multipliée par le coût moyen ». C'est :

- 73,7 % du temps : zéro incident, coût 0 € ;
- 22,5 % du temps : un incident, coût = un tirage dans la lognormale ;
- 3,4 % du temps : deux incidents, coût = la somme de deux tirages ;
- etc.

La distribution de S est un **mélange** de ces cas. Elle a une masse ponctuelle
en 0 (d'où la médiane à 0 €) et une longue queue à droite.

### Ce qu'on sait analytiquement, et ce qu'on ne sait pas

L'espérance se calcule à la main, par la **formule de Wald** :

$$\mathbb{E}[S] = \mathbb{E}[N] \cdot \mathbb{E}[X] = \lambda \cdot e^{\mu + \sigma^2/2}$$

La variance aussi :

$$\text{Var}(S) = \lambda \cdot \mathbb{E}[X^2]$$

Mais **la fonction de répartition de S n'a pas de forme fermée**. Or VaR 99 et
TVaR 99 sont des quantiles de S. Il n'existe pas de formule à évaluer : soit on
passe par des approximations (Panjer, transformée de Fourier rapide, Edgeworth),
soit on simule.

**C'est la réponse à « pourquoi Monte Carlo plutôt qu'une formule ».** Ce n'est
pas de la paresse : la moyenne est analytique et le code pourrait s'en passer,
mais ce n'est pas la moyenne qu'on veut, c'est la forme complète de la
distribution.

### L'algorithme, en trois lignes

```
pour chaque année simulée a = 1 … 100 000 :
    pour chaque type d'attaque t :
        n ← tirage Poisson(λ_t)
        S_a += somme de n tirages Lognormale(μ_t, σ_t)
```

Puis on lit les métriques sur les 100 000 valeurs de S_a obtenues.

### Combien d'années simuler ?

L'erreur de Monte Carlo décroît en 1/√n. Pour estimer un quantile à 99 %, seules
1 % des années comptent : sur 100 000 années simulées, la VaR 99 s'appuie sur
1 000 observations, et la TVaR 99 les moyenne. Sur 1 000 années, elle
s'appuierait sur 10 — inutilisable. **C'est ce qui fixe le nombre d'années, pas
la moyenne**, qui serait stable bien avant.

---

## 4. AAL, VaR, TVaR

### Définitions

Soit S la perte annuelle, de fonction de répartition F.

| Mesure | Définition | Lecture |
|---|---|---|
| **AAL** | E[S] | *Average Annual Loss* — la moyenne. La ligne budgétaire. |
| **VaR_α** | inf{ s : F(s) ≥ α } | Le quantile d'ordre α. « Une année sur 20 atteint ce niveau. » |
| **TVaR_α** | E[S \| S ≥ VaR_α] | La moyenne des pertes **au-delà** de la VaR. |

TVaR s'appelle aussi *Expected Shortfall*, *CVaR* ou *Conditional Tail
Expectation*. On a toujours **TVaR_α ≥ VaR_α** par construction : la moyenne
d'un ensemble dont le plus petit élément vaut VaR ne peut pas descendre en
dessous. Le projet en fait une invariante testée.

### Intuition : pourquoi les deux

La VaR dit **où commence la zone rouge**. Elle ne dit rien de ce qui s'y passe.
Deux entreprises peuvent avoir la même VaR 99 et des TVaR 99 dans un rapport de
dix — l'une perd un peu plus que la VaR dans ses pires années, l'autre perd
beaucoup plus.

La VaR a aussi un défaut théorique connu : **elle n'est pas sous-additive**. On
peut construire deux portefeuilles A et B tels que VaR(A + B) > VaR(A) + VaR(B),
ce qui contredit l'idée que diversifier réduit le risque. La TVaR, elle, est une
**mesure de risque cohérente** au sens d'Artzner et al. (1999) : monotone,
sous-additive, homogène et invariante par translation. C'est pour cette raison
que Solvabilité II et Bâle se sont déplacés vers l'*expected shortfall*.

### Les valeurs du projet

| | valeur | lecture |
|---|---:|---|
| AAL | 273 704 € | budget annuel moyen |
| année médiane | 0 € | 73,7 % des années ne coûtent rien |
| VaR 95 | 816 323 € | une année sur vingt |
| TVaR 95 | 4 820 816 € | moyenne des 5 % pires |
| VaR 99 | 6 665 810 € | une année sur cent |
| TVaR 99 | 15 134 257 € | moyenne des 1 % pires |

**Le rapport TVaR 95 / VaR 95 vaut 5,9.** Il dit tout de la forme de la
distribution : une fois passé le seuil de la mauvaise année, la perte typique
est presque six fois ce seuil. C'est ce qu'on appelle une queue lourde.

---

## 5. Pondération douce et taille d'échantillon effective de Kish

### Le problème

On veut ajuster une loi de sévérité « pour une ETI Retail de 1 200 salariés à
maturité 55 ». L'approche évidente : filtrer la base externe sur ce profil.

Sur les données du projet, ce filtre exact laisse **112 incidents sur 1 598**,
répartis sur neuf types d'attaque — donc aucun type ne dispose d'un échantillon
crédible. Mathématiquement propre, pratiquement inutilisable.

### La solution : pondérer plutôt que filtrer

Chaque incident reçoit un poids continu selon sa ressemblance :

$$w_i = w_{\text{secteur}} \times w_{\text{taille}} \times \exp\left(-\frac{d_i^2}{2h^2}\right), \qquad d_i = |\text{maturité}_i - 55|$$

Le troisième facteur est un **noyau gaussien** de largeur de bande h = 15 : un
pair de maturité 55 pèse 1, un pair de maturité 70 pèse e^(−225/450) = 0,607, un
pair de maturité 100 pèse e^(−2025/450) = 0,011. La décroissance est douce, donc
personne n'est jeté, mais les lointains ne pèsent presque rien.

### Ce que la pondération coûte : n_eff de Kish

**Définition.** Pour des poids w₁ … wₙ, la taille d'échantillon effective de
Kish vaut

$$n_{\text{eff}} = \frac{\left(\sum_i w_i\right)^2}{\sum_i w_i^2}$$

**Intuition.** C'est le nombre d'observations *de poids égal* qui porteraient
autant d'information que l'échantillon pondéré. Elle vaut n quand tous les poids
sont égaux, et chute dès qu'un petit nombre d'observations domine.

**Exemple chiffré.** Quatre incidents, poids 1 ; 0,5 ; 0,25 ; 0,1 :

```
Σw  = 1 + 0,5 + 0,25 + 0,1 = 1,85
Σw² = 1 + 0,25 + 0,0625 + 0,01 = 1,3225
n_eff = 1,85² / 1,3225 = 3,4225 / 1,3225 = 2,588
```

Quatre incidents ne valent que 2,59 incidents « pleins ».

Deux cas limites, pour caler l'intuition :

| poids | n_eff | lecture |
|---|---|---|
| (0,2 ; 0,2 ; 0,2 ; 0,2) | **4,000** | poids égaux → aucune perte |
| (1 ; 0,5 ; 0,25 ; 0,1) | 2,588 | décroissance douce |
| (1 ; 0,01 ; 0,01 ; 0,01) | **1,061** | un pair domine → il reste ≈ 1 observation |

**Remarquez le point contre-intuitif** : n_eff ne mesure pas la *taille* des
poids mais leur **régularité**. Quarante pairs tous pondérés à 0,01 donnent
n_eff = 40. Ce qui détruit n_eff, c'est un pair très proche noyé parmi des pairs
lointains.

### Dans le projet

Le type `supply_chain` compte n = 78 incidents pour **n_eff = 52,3**. Le seuil
de repli est fixé à 30 : en dessous, le type hérite de la distribution *poolée*
(ajustée sur tous les types), et la substitution est enregistrée plutôt que
dissimulée.

---

## 6. Statistique de Kolmogorov–Smirnov

### Définition

Pour un échantillon x₁ ≤ … ≤ xₙ et une loi théorique F, la statistique de
Kolmogorov–Smirnov est l'écart vertical maximal entre la fonction de répartition
empirique Fₙ et F :

$$D_n = \sup_x |F_n(x) - F(x)|$$

Comme Fₙ est en escalier, le supremum est atteint à un point de saut, et il faut
tester **les deux côtés** de chaque marche :

$$D_n = \max_i \max\left( \left|\tfrac{i}{n} - F(x_i)\right|,\ \left|\tfrac{i-1}{n} - F(x_i)\right| \right)$$

### Exemple chiffré

Quatre observations, et la loi théorique leur attribue F = (0,20 ; 0,45 ; 0,70 ; 0,95) :

| i | F(xᵢ) | i/n | (i−1)/n | \|i/n − F\| | \|(i−1)/n − F\| |
|---|---|---|---|---|---|
| 1 | 0,20 | 0,25 | 0,00 | 0,05 | **0,20** |
| 2 | 0,45 | 0,50 | 0,25 | 0,05 | **0,20** |
| 3 | 0,70 | 0,75 | 0,50 | 0,05 | **0,20** |
| 4 | 0,95 | 1,00 | 0,75 | 0,05 | **0,20** |

D = **0,20**.

### Le seuil

Pour un test à 5 %, la valeur critique asymptotique vaut environ 1,36 / √n. Avec
n_eff = 52 : 1,36 / √52 = **0,189**.

Le projet mesure **D = 0,118** sur `supply_chain`, donc l'ajustement n'est pas
rejeté.

### La limite qu'il faut connaître

**KS est peu puissant dans les queues.** L'écart |Fₙ − F| est mécaniquement
borné là où F approche 0 ou 1, donc le maximum est presque toujours atteint au
centre de la distribution. Un modèle qui décrit bien le corps et mal les
extrêmes passera le test.

C'est précisément pourquoi le projet publie **aussi** un QQ-plot (qui montre
*où* le modèle se trompe) et une **contre-preuve de Pareto** (§11) : sur cinq
ajustements sur neuf, une loi de Pareto décrit mieux les extrêmes que la
lognormale retenue.

---

# Partie II — les neuf chantiers de modélisation

## 7. Sensibilité et élasticité

> Chantier : **Report the answer's sensitivity to p_materialize** (phase 1, S)

### Le contexte

Le moteur convertit les attaques détectées en incidents à perte par un scalaire :

$$\lambda_{\text{incident}} = \lambda_{\text{détecté}} \times p, \qquad p = 1{,}946 \times 10^{-4}$$

soit une détection sur 5 138 qui finit en perte. Ce nombre est aujourd'hui
calibré pour que le résultat corresponde au taux de base des pairs, et il
n'apparaît que dans la trace.

### Définition

L'**élasticité** d'une sortie y par rapport à une entrée x est la variation
relative de y pour une variation relative de x :

$$\varepsilon_{y/x} = \frac{\partial \ln y}{\partial \ln x} = \frac{x}{y}\frac{\partial y}{\partial x}$$

Une élasticité de 1 signifie « +10 % sur l'entrée donne +10 % sur la sortie ».

### Les maths

Ici, AAL = λ_incident · E[X] = λ_détecté · p · E[X]. L'AAL est donc **linéaire
en p**, et son élasticité vaut exactement **1**.

```
∂AAL/∂p = λ_détecté · E[X] = AAL / p
ε = (p / AAL) · (AAL / p) = 1
```

### Exemple chiffré

| p multiplié par | λ_incident | AAL |
|---|---:|---:|
| 0,5 | 0,1526 | 136 852 € (−50 %) |
| 0,8 | 0,2442 | 218 963 € (−20 %) |
| **1,0** | **0,3052** | **273 704 €** |
| 1,25 | 0,3816 | 342 130 € (+25 %) |
| 2,0 | 0,6105 | 547 408 € (+100 %) |

### Le piège

**L'AAL est linéaire en p. La VaR et la TVaR ne le sont pas.** Doubler p ne
double pas la VaR 99 : cela change la *forme* de la distribution composée, parce
que la probabilité d'avoir **au moins deux** incidents dans la même année passe
de 3,81 % à 12,54 %. Un tableau de sensibilité doit donc être **simulé**, pas extrapolé — et
c'est ce qui distingue ce chantier d'une simple règle de trois.

### Ce que ça change

p est le nombre le plus influent du pipeline et le moins visible. Le chantier
consiste à le balayer comme le sont déjà le seuil de sévérité et la fenêtre de
session, et à afficher le résultat à côté de la grille 3×3 existante.

---

## 8. Backtesting : CRPS, PIT, validation croisée

> Chantier : **Backtest against the incident base** (phase 1, M)

### Le problème

Tous les tests du projet vérifient la **cohérence interne** : invariantes,
reproductibilité, arithmétique. Aucun ne confronte la sortie à la réalité
observée. Un modèle peut être parfaitement cohérent et parfaitement faux.

### Le concept clé : une règle de score propre

**Définition.** Une règle de score S(F, y) évalue une prévision *probabiliste* F
face à une observation réalisée y. Elle est **propre** (*proper*) si elle est
optimisée en espérance par la vraie loi : annoncer autre chose que ce qu'on
croit ne peut pas améliorer le score attendu.

C'est essentiel : une règle non propre récompense le mensonge. Avec l'erreur
quadratique sur la moyenne seule, par exemple, on est incité à annoncer une
distribution artificiellement étroite.

### CRPS

**Définition.** Le *Continuous Ranked Probability Score* :

$$\text{CRPS}(F, y) = \int_{-\infty}^{+\infty} \big( F(x) - \mathbb{1}\{x \ge y\} \big)^2 \, dx$$

On compare la fonction de répartition prévue à la fonction de répartition
« parfaite » de l'observation (une marche à y). Plus c'est petit, mieux c'est.

**La forme utilisable.** Pour un ensemble de tirages, il existe une écriture
équivalente bien plus commode :

$$\text{CRPS}(F, y) = \mathbb{E}|X - y| - \tfrac{1}{2}\mathbb{E}|X - X'|$$

où X et X′ sont deux tirages indépendants de F. Le premier terme récompense la
**justesse**, le second pénalise la **dispersion** — un modèle qui prévoit
n'importe quoi très largement est puni.

**Exemple chiffré.** Ensemble de trois tirages {1, 2, 4}, observation y = 3.

Premier terme :
```
E|X − y| = (|1−3| + |2−3| + |4−3|) / 3 = (2 + 1 + 1)/3 = 1,3333
```

Second terme — les neuf paires possibles :
```
|1−1| |1−2| |1−4|     0  1  3
|2−1| |2−2| |2−4|  =  1  0  2
|4−1| |4−2| |4−4|     3  2  0
E|X − X'| = (0+1+3+1+0+2+3+2+0) / 9 = 12/9 = 1,3333
```

```
CRPS = 1,3333 − 0,5 × 1,3333 = 0,6667
```

Trois points de comparaison :

| prévision | CRPS | lecture |
|---|---:|---|
| ensemble {1, 2, 4} | 0,667 | correcte mais dispersée |
| déterministe X = 3 | **0,000** | parfaite |
| déterministe X = 2 | 1,000 | = l'erreur absolue |
| ensemble {10, 11, 12} | 7,556 | biaisée : lourdement punie |

**Propriété remarquable** : pour une prévision déterministe, le CRPS se réduit à
l'erreur absolue. Le CRPS est donc la généralisation naturelle de la MAE aux
prévisions probabilistes, et se lit dans l'unité de la variable (ici, des euros).

### PIT

**Définition.** La *Probability Integral Transform* : si Y suit vraiment la loi
F, alors U = F(Y) suit une loi **uniforme sur [0, 1]**.

**Intuition.** On demande au modèle, pour chaque observation réelle : « à quel
percentile de ta prévision cette valeur se situe-t-elle ? ». Si le modèle est
calibré, les réponses doivent se répartir uniformément — autant d'observations
au 10ᵉ percentile qu'au 90ᵉ.

**Diagnostic par la forme de l'histogramme** — c'est là tout son intérêt :

| forme | interprétation |
|---|---|
| plate | modèle calibré |
| en **U** (creux au milieu) | prévisions **trop étroites** : la réalité sort des bornes trop souvent |
| en **cloche** (bosse au milieu) | prévisions **trop larges** : le modèle est trop prudent |
| pente vers la droite | modèle **sous-estime** systématiquement |
| pente vers la gauche | modèle **surestime** systématiquement |

**Exemple chiffré.** Modèle lognormal(μ = 12, σ = 2), cinq pertes observées :

| y observé | u = F(y) |
|---:|---:|
| 45 000 | 0,2602 |
| 120 000 | 0,4394 |
| 260 000 | 0,5926 |
| 900 000 | 0,8037 |
| 1 800 000 | 0,8853 |

Moyenne des u = **0,596**, au lieu de 0,5 attendu, et trois valeurs sur cinq
sont au-dessus de la médiane : le modèle **sous-estime** légèrement. Sur cinq points
la conclusion n'est évidemment pas significative — mais le mécanisme est là.

### La difficulté propre à ce projet

Le volet fréquence est simple et se ferait en premier : couper la fenêtre de
télémétrie en deux et vérifier que le taux estimé sur la première moitié prédit
la seconde.

Le volet sévérité est plus subtil qu'il n'y paraît. **Le modèle prédit les
pertes de *cette* entreprise, alors que les incidents mis de côté appartiennent
à *d'autres* entreprises.** Un backtest naïf noterait donc le schéma de
pondération, pas l'ajustement. Le faire proprement suppose une **validation
croisée « leave-one-company-out »** : pour chaque organisation retirée, prédire
ses pertes à partir de son propre groupe de pairs, et scorer cette prédiction.

---

## 9. Crédibilité Gamma-Poisson

> Chantier : **Gamma-Poisson credibility: blend telemetry with base rates**
> (phase 3, M) — décrit comme *« la première chose à construire ensuite »*

### Le problème

Le moteur ancre aujourd'hui le taux d'incidents **entièrement** sur la base de
pairs : 0,3052 par organisation-année. La télémétrie ne fournit que le *mix* par
type d'attaque. Autrement dit, sept mois d'observation propre à l'entreprise
pèsent **zéro** dans la fréquence.

C'est l'extrême opposé de la première version, qui faisait confiance à 100 % à
la télémétrie et sortait 12,5 Md€. Aucun des deux extrêmes n'est bon.

### Définition : la conjugaison Gamma-Poisson

La loi Gamma(α, β) est le **prior conjugué** de la loi de Poisson. « Conjugué »
signifie que le posterior appartient à la même famille que le prior, ce qui rend
la mise à jour purement algébrique — aucune intégration.

Densité Gamma, paramétrée en *rate* (β = taux, pas échelle) :

$$\pi(\lambda) = \frac{\beta^\alpha}{\Gamma(\alpha)} \lambda^{\alpha-1} e^{-\beta\lambda}, \qquad \mathbb{E}[\lambda] = \frac{\alpha}{\beta}, \quad \text{Var}(\lambda) = \frac{\alpha}{\beta^2}$$

**La règle de mise à jour.** Si on observe x événements sur n années
d'exposition :

$$\alpha_{\text{post}} = \alpha_0 + x \qquad \beta_{\text{post}} = \beta_0 + n$$

C'est tout. Le posterior est Gamma(α₀ + x, β₀ + n).

### Le lien avec la crédibilité

La moyenne a posteriori se réécrit **exactement** comme une moyenne pondérée :

$$\mathbb{E}[\lambda \mid \text{données}] = \frac{\alpha_0 + x}{\beta_0 + n} = Z \cdot \underbrace{\frac{x}{n}}_{\text{télémétrie}} + (1 - Z) \cdot \underbrace{\frac{\alpha_0}{\beta_0}}_{\text{pairs}}, \qquad Z = \frac{n}{n + \beta_0}$$

C'est la **formule de crédibilité de Bühlmann**, retrouvée par un chemin
bayésien. Le facteur Z ∈ [0, 1] est le poids accordé à l'observation propre. Et
β₀ **est** le k de la formule Z = n/(n+k) : il s'interprète comme le nombre
d'années-organisation d'expérience que le prior « vaut ».

### Exemple chiffré complet

**Prior.** On veut une moyenne de 0,31 (le taux des pairs) avec une incertitude
raisonnable. On pose α₀ = 3,1 et β₀ = 10 :

```
moyenne  = α₀/β₀  = 3,1/10       = 0,3100
variance = α₀/β₀² = 3,1/100      = 0,0310
écart-type                       = 0,1761
```

β₀ = 10 signifie : « ce prior vaut dix années-organisation d'observation ».

**Observation.** L'entreprise a été observée 0,581 année (212 jours) et a subi
1 incident à perte.

**Posterior :**
```
α₁ = 3,1 + 1     = 4,100
β₁ = 10 + 0,581  = 10,581
E[λ | données] = 4,100 / 10,581 = 0,3875
```

**Vérification par la formule de crédibilité :**
```
Z = 0,581 / (0,581 + 10) = 0,0549
λ_télémétrie = 1 / 0,581 = 1,7212      ← taux brut observé, très bruité
blend = 0,0549 × 1,7212 + 0,9451 × 0,3100
      = 0,0945 + 0,2930
      = 0,3875   ✓ identique
```

**Lisez ce que le mécanisme a fait.** La télémétrie brute suggère 1,72 incident
par an — parce qu'un seul incident sur sept mois s'extrapole mal. Le prior dit
0,31. Le blend retient 0,3875 : la télémétrie a **déplacé** l'estimation vers le
haut de 25 %, sans lui laisser imposer une valeur absurde. C'est exactement le
comportement recherché.

**Et Z croît avec l'observation :**

| exposition | Z | poids de la télémétrie |
|---|---:|---:|
| 0,581 an (aujourd'hui) | 0,055 | 5,5 % |
| 5 ans | 0,333 | 33,3 % |
| 20 ans | 0,667 | 66,7 % |
| 100 ans | 0,909 | 90,9 % |

### Pourquoi ce n'est pas fait

**Rien dans les données ne fixe k.** J'ai posé β₀ = 10 dans l'exemple ; j'aurais
pu poser 2 ou 50, et le résultat aurait changé du tout au tout. Or k décide
*combien la preuve propre du client compte* — précisément le jugement que le
cadre de crédibilité est censé rendre explicite. Le choisir au feeling
reviendrait à cacher l'arbitraire à l'intérieur d'une formule d'allure
rigoureuse.

Estimer k proprement demande **plusieurs entreprises observées**, pour séparer
la variance *entre* organisations de la variance *au sein* d'une organisation
(c'est ce que fait l'estimateur de Bühlmann–Straub). Avec une seule entreprise,
c'est impossible — et c'est aussi ce qui fait de ce chantier une fonctionnalité
naturelle une fois le produit multi-clients (phase 2).

---

## 10. Le cadre FAIR

> Chantiers : **Model p_materialize** (phase 3, L) et **Control effectiveness**
> (phase 3, L)

### Définition

**FAIR** — *Factor Analysis of Information Risk* — est une ontologie standard
qui décompose le risque en facteurs mesurables séparément. Le fragment qui nous
intéresse :

```
                    Risque
                       │
        ┌──────────────┴──────────────┐
   Fréquence des                  Magnitude
   événements de perte            de la perte
   (LEF)                          (LM)
        │
   ┌────┴────┐
Fréquence     Vulnérabilité
des menaces   (probabilité qu'une
(TEF)          menace aboutisse)
```

$$\text{LEF} = \text{TEF} \times \text{Vuln}$$

- **TEF** (*Threat Event Frequency*) — ce qui arrive. Fonction de l'exposition,
  du secteur, de l'attractivité.
- **Vulnérabilité** — ce qui passe. Fonction de la qualité des contrôles.
- **LEF** (*Loss Event Frequency*) — ce qui coûte.

### La correspondance avec le projet

Le moteur fait déjà exactement ça, mais sans le dire et sans structure :

| FAIR | dans le moteur | valeur |
|---|---|---|
| TEF | λ_détecté | 1 568,5 / an |
| Vulnérabilité | p_materialize | 1,946 × 10⁻⁴ |
| LEF | λ_incident | **0,3052 / an** |

`1 568,5 × 1,946 × 10⁻⁴ = 0,3052` ✓

### Ce que le chantier propose

Remplacer le scalaire par une fonction de la maturité :

$$p = p_{\text{échec des contrôles}}(\text{maturité}) \times p_{\text{impact} \mid \text{échec}}(\text{actif}, \text{type})$$

**Exemple chiffré de ce que ça changerait**, à TEF constant :

| maturité | Vulnérabilité | LEF résultant |
|---|---:|---:|
| 35 | 3,00 × 10⁻⁴ | 0,4705 / an |
| **55 (aujourd'hui)** | 1,946 × 10⁻⁴ | **0,3052 / an** |
| 75 | 1,20 × 10⁻⁴ | 0,1882 / an |

Passer de 55 à 75 réduirait la fréquence de perte de 38 %, et donc l'AAL
d'autant. **Aujourd'hui, ce gain est structurellement inexprimable** : une
entreprise à maturité 75 hérite du même ancrage sur les pairs. C'est un mauvais
signal pour un outil censé justifier un budget de sécurité.

### Pourquoi ce n'est pas fait — l'argument le plus important du document

Calibrer la courbe maturité → vulnérabilité suppose une régression de la
fréquence d'incidents sur le score de maturité. **Cette régression a besoin d'un
dénominateur d'exposition que la base ne contient pas.**

Détaillons, parce que c'est subtil. La base recense des **incidents**, pas des
**années-organisation à risque**. Si l'organisation A (maturité 35) apparaît
trois fois et l'organisation B (maturité 75) une fois, on ne peut pas conclure
que A est trois fois plus vulnérable : A est peut-être simplement restée plus
longtemps dans le périmètre de collecte, ou plus grande, ou mieux instrumentée
en détection — donc plus susceptible de *déclarer*.

Sans le dénominateur, on régresse un numérateur sur une covariable et on obtient
un coefficient d'allure confiante qui ne mesure rien. **Un scalaire visible qui
fait un travail est plus honnête qu'un modèle qui suggère une connaissance
absente.**

### Le second piège : le double comptage

Le chantier *Control effectiveness* étend l'idée à la sévérité. Danger réel :
**la télémétrie reflète déjà les contrôles de cette entreprise**. Un parc bien
défendu génère des détections différentes — moins d'attaques abouties, plus de
blocages précoces. Appliquer par-dessus une décote de maturité déflaterait deux
fois le même effet.

Bien faire suppose donc de savoir **ce que chaque source encode déjà**, ce qui
est une question de conception plus que de statistique.

---

## 11. Théorie des valeurs extrêmes : POT et GPD

> Chantier : **GPD tail via peaks-over-threshold** (phase 3, M)

### Le problème

Le moteur signale lui-même que sur **cinq ajustements sur neuf**, une queue de
Pareto décrit mieux les extrêmes que la lognormale retenue — deux fois avec
α < 1. Or VaR 99 et TVaR 99 sont presque entièrement faites de cette queue.

### Le théorème fondateur

**Pickands–Balkema–de Haan (1974–1975).** Pour une très large classe de lois, la
distribution des dépassements au-dessus d'un seuil u converge, quand u tend vers
le point terminal, vers une **loi de Pareto généralisée** (GPD) :

$$P(X - u \le z \mid X > u) \xrightarrow[u \to \infty]{} G_{\xi,\sigma}(z) = 1 - \left(1 + \frac{\xi z}{\sigma}\right)^{-1/\xi}$$

C'est l'analogue, pour les queues, de ce que le théorème central limite est pour
les moyennes : **quelle que soit** la loi de départ, la queue prend une forme
universelle à deux paramètres. C'est ce qui rend l'exercice légitime plutôt
qu'arbitraire.

### Le paramètre de forme ξ

ξ (xi) est **tout** ce qui compte. On note souvent α = 1/ξ (l'indice de queue de
Pareto).

| ξ | α = 1/ξ | comportement | moments |
|---|---|---|---|
| ξ < 0 | — | queue bornée | tous finis |
| ξ = 0 | ∞ | queue exponentielle | tous finis |
| 0 < ξ < ½ | α > 2 | queue lourde | moyenne et variance finies |
| ½ ≤ ξ < 1 | 1 < α ≤ 2 | très lourde | moyenne finie, **variance infinie** |
| ξ ≥ 1 | α ≤ 1 | extrême | **moyenne infinie** |

**« Moyenne infinie » n'est pas une abstraction.** Cela veut dire que la moyenne
empirique ne converge pas : plus on simule d'années, plus l'AAL monte, sans
limite. Un modèle avec α < 1 ne peut pas produire une AAL stable — et deux types
du projet sont dans ce régime.

### L'estimateur de Hill

Pour une queue de Pareto, l'estimateur le plus simple de α, à partir des k
dépassements x₍₁₎ … x₍ₖ₎ au-dessus de u :

$$\hat\alpha_{\text{Hill}} = \left( \frac{1}{k} \sum_{i=1}^{k} \ln \frac{x_{(i)}}{u} \right)^{-1}$$

**Exemple chiffré.** Seuil u = 2 M€, cinq dépassements :

```
2,4 M€   3,1 M€   4,8 M€   7,2 M€   15,0 M€
```

Les log-ratios :
```
ln(2,4/2,0)  = 0,1823
ln(3,1/2,0)  = 0,4383
ln(4,8/2,0)  = 0,8755
ln(7,2/2,0)  = 1,2809
ln(15,0/2,0) = 2,0149
moyenne      = 0,9584
```

```
α̂ = 1 / 0,9584 = 1,0434       (ξ = 0,9584)
```

α ≈ 1,04 : **à peine** au-dessus du seuil de moyenne infinie. Pour une loi de
Pareto pure de paramètres (u, α), la moyenne vaut α·u/(α−1), ici
1,0434 × 2 M€ / 0,0434 ≈ 48 M€ — mais l'estimation est si proche de 1 que cette
valeur n'a aucune stabilité. C'est le genre de résultat qui doit déclencher de
la prudence, pas une décimale supplémentaire.

Trois régimes, pour comparer :

| α | moyenne (u = 2 M€) | variance |
|---|---:|---|
| 0,9 | **infinie** | infinie |
| 1,5 | 6 000 000 € | infinie |
| 2,5 | 3 333 333 € | finie |

### Le choix du seuil : le compromis central

**Trop bas** → on inclut des points du corps de la distribution, la convergence
vers la GPD n'est pas atteinte, l'estimation est **biaisée**.
**Trop haut** → il reste trop peu de dépassements, l'estimation est
**très variable**.

L'outil standard est le **graphique de vie résiduelle moyenne** (*mean residual
life plot*) : on trace e(u) = E[X − u | X > u] contre u. Propriété : pour une
GPD, cette fonction est **linéaire** en u. On choisit donc u au point à partir
duquel la courbe devient droite.

### Le modèle épissé

En pratique on ne remplace pas la lognormale, on la **recolle** avec la GPD :

$$F(x) = \begin{cases} F_{\text{lognormale}}(x) & x \le u \\[4pt] F(u) + \big(1 - F(u)\big)\, G_{\xi,\sigma}(x - u) & x > u \end{cases}$$

Corps lognormal, queue GPD, continuité en u. La fonction `sample()` tirerait
dans le mélange.

### Pourquoi ce n'est pas fait

**Trois des huit types ont moins de 15 dépassements au-dessus du 90ᵉ percentile
pondéré** — dont `data_breach`, qui porte la deuxième plus grosse moyenne et
donc la queue la plus intéressante à modéliser. Ajuster une GPD sur une douzaine
de points produit un ξ d'une variance énorme : l'intervalle de confiance
recouvrirait à la fois « variance finie » et « moyenne infinie », ce qui ne
décide rien.

Le choix retenu a donc été de **publier le diagnostic sans faire l'ajustement**,
et de lire VaR 99 et TVaR 99 comme des bornes basses.

---

## 12. Écrêtage contre troncature

> Chantier : **Derive the loss cap from the company's own exposure** (phase 3, M)

### Le contexte

Une lognormale n'a pas de borne supérieure. À σ = 2,58 et sur 100 000 années,
elle finit par tirer un incident coûtant plus que l'entreprise ne vaut : sans
plafond, la pire année simulée du projet atteignait **3,8 milliards d'euros**
pour une ETI de 1 200 personnes. Le moteur écrête donc chaque perte unitaire au
99,9ᵉ percentile des pertes réellement observées chez les pairs, soit
**23 476 094 €**.

### Deux opérations différentes

| | définition | effet |
|---|---|---|
| **Écrêtage** (*clipping*) | X′ = min(X, C) | crée une **masse ponctuelle** en C |
| **Troncature** | on conditionne : X′ ~ X \| X < C | **redistribue** la masse, aucun atome |

C'est la distinction que le chantier propose de corriger : le moteur écrête au
moment du tirage ; il serait statistiquement plus propre de tronquer au moment
de l'ajustement.

### Les maths

Soit X lognormale(μ, σ) et C le plafond.

**Écrêtage :**
$$\mathbb{E}[\min(X, C)] = \underbrace{\mathbb{E}[X \cdot \mathbb{1}\{X < C\}]}_{\text{partie basse}} + C \cdot P(X \ge C)$$

avec la formule utile (elle vaut la peine d'être retenue) :

$$\mathbb{E}[X \cdot \mathbb{1}\{X < C\}] = e^{\mu + \sigma^2/2} \cdot \Phi\!\left(\frac{\ln C - \mu - \sigma^2}{\sigma}\right)$$

**Troncature :**
$$\mathbb{E}[X \mid X < C] = \frac{\mathbb{E}[X \cdot \mathbb{1}\{X < C\}]}{P(X < C)}$$

### Exemple chiffré

Lognormale de médiane 200 000 € (μ = ln 200 000 = 12,206), σ = 1,5, plafond
C = 5 000 000 €.

```
P(X > C)                    = 0,015940     (1,594 %)
E[X]            sans plafond = 616 043 €
E[X · 1{X<C}]                = 456 386 €
E[min(X,C)]     écrêtage     = 456 386 + 5 000 000 × 0,015940 = 536 085 €
E[X | X<C]      troncature   = 456 386 / 0,984060             = 463 778 €
```

**Trois lectures :**

1. **L'écrêtage retire 13 %** de la moyenne (616 043 → 536 085). Sur les données
   réelles du projet, le plafond retire **37,5 % de l'AAL** et **52 % de la
   TVaR 99** — l'hypothèse pèse autant que l'ajustement de sévérité lui-même.
2. **Écrêtage et troncature ne donnent pas le même résultat** : 536 085 contre
   463 778, soit 16 % d'écart. L'écrêtage garde la masse de la queue en la
   tassant sur C ; la troncature la supprime et renormalise.
3. **L'écrêtage laisse un atome de probabilité 0,0159 en C.** Toutes les années
   contenant un incident écrêté coûtent *exactement* le même montant. C'est
   visible sur l'histogramme de la page /simulation, sous la forme d'un pic à
   l'extrême droite — le projet l'annote plutôt que de le masquer.

### Ce que le chantier changerait

Le plafond actuel est une propriété de la **population de pairs**, pas de cette
entreprise. Une ETI de 1 200 personnes et un industriel de 4 000 partagent le
même plafond, ce qui ne peut pas être correct : ce qu'une organisation peut
perdre dépend de ce qu'elle possède.

La version aboutie : un plafond d'exposition construit sur des données qu'une
mission de quantification possède déjà — chiffre d'affaires, actifs au bilan,
nombre d'enregistrements exposés au sens RGPD, plafonds de responsabilité
contractuels — puis

$$C = \min(C_{\text{interruption}},\ C_{\text{responsabilité données}},\ \dots)$$

et une **troncature à l'ajustement** plutôt qu'un écrêtage au tirage.

**Pourquoi ce n'est pas fait** : les données du cas ne contiennent aucun profil
financier de l'entreprise cible. En inventer un pour justifier une borne plus
sophistiquée aurait été pire que de lire la borne sur les preuves disponibles et
de le dire.

---

## 13. Dépendance et copules

> Chantier : **Dependence between attack types** (phase 3, M)

### Le problème

La simulation tire le compte de Poisson de chaque type d'attaque
**indépendamment**. Les campagnes réelles ne fonctionnent pas ainsi : une vague
de phishing amène du vol d'identifiants, qui amène un rançongiciel.

### Pourquoi l'indépendance minimise le risque

Résultat de base : pour deux variables aléatoires,

$$\text{Var}(X + Y) = \text{Var}(X) + \text{Var}(Y) + 2\rho\sqrt{\text{Var}(X)\text{Var}(Y)}$$

**L'espérance ne dépend pas de ρ** — E[X+Y] = E[X] + E[Y] toujours. Mais la
variance, si. Donc l'AAL est insensible à la dépendance, tandis que **VaR et
TVaR ne le sont pas**.

**Exemple chiffré.** Deux types, écart-type 1 M€ chacun :

| ρ | Var(X+Y) | écart-type du total |
|---|---:|---:|
| 0 (indépendants) | 2,0 × 10¹² | 1 414 214 € |
| 0,5 | 3,0 × 10¹² | 1 732 051 € |
| 1 (comonotones) | 4,0 × 10¹² | 2 000 000 € |

Passer de l'indépendance à la dépendance parfaite multiplie l'écart-type par
√2 ≈ 1,414. **Supposer l'indépendance, c'est donc supposer le meilleur cas** —
l'agrégat est trop bien élevé, et les deux mesures de queue sont sous-estimées.

### Sur les comptes d'événements

**Exemple chiffré.** Deux types à λ = 0,15 chacun.

```
Indépendants : P(les deux ≥ 1) = (1 − e^−0,15)²  = 0,139292²  = 0,019402
Comonotones  : P(les deux ≥ 1) = 1 − e^−0,15                  = 0,139292
```

Un facteur **7,2** sur la probabilité de l'année à double incident. Or ce sont
exactement ces années qui font la queue de la distribution annuelle.

### Définition : copule

**Théorème de Sklar (1959).** Toute loi jointe F se décompose de façon unique
(sur le support continu) en ses lois marginales et une **copule** C :

$$F(x_1, \dots, x_d) = C\big(F_1(x_1), \dots, F_d(x_d)\big)$$

où C est une fonction de répartition sur [0,1]^d à marges uniformes.

**Intuition.** La copule sépare complètement deux questions :
- « comment se comporte chaque type isolément ? » → les marginales, déjà ajustées ;
- « comment se comportent-ils ensemble ? » → la copule, à ajouter.

C'est ce qui permet de greffer la dépendance **sans toucher** aux ajustements
existants — argument décisif ici, puisque les marginales sont le fruit du
travail des slides 8 à 10.

### Copule gaussienne ou copule de Student

- **Gaussienne** : entièrement décrite par une matrice de corrélation. Simple,
  mais **dépendance de queue nulle** — les événements extrêmes y deviennent
  asymptotiquement indépendants.
- **Student (t)** : ajoute un degré de liberté ν et possède une **dépendance de
  queue non nulle**. Les extrêmes arrivent ensemble.

Pour du risque, la distinction est loin d'être académique : c'est en substance
le reproche fait aux copules gaussiennes dans la crise de 2008.

### Mise en œuvre

La matrice de corrélation s'estimerait sur la **co-occurrence de types d'attaque
au sein d'un même `company_id`** dans la base d'incidents — plusieurs
organisations y apparaissent plus d'une fois, ce qui est précisément le signal
nécessaire.

### Pourquoi ce chantier a monté dans la liste

Un point noté dans `next_steps.md` et qui mérite d'être compris. **La
calibration a augmenté la valeur de ce chantier.** À λ = 0,31, le total annuel
est dominé par la question « y a-t-il un incident, oui ou non », donc la
corrélation entre types façonne matériellement la queue. À l'ancien λ ≈ 9 168,
l'agrégat était si lisse — par simple loi des grands nombres — que la dépendance
n'y changeait presque rien.

---

## 14. Allocation par actif

> Chantier : **Asset-level loss allocation by criticality** (phase 3, M)

### Le problème

La sortie est un chiffre unique pour toute l'entreprise. La question qu'un RSSI
pose réellement est « quels actifs le portent ? ». Le moteur connaît déjà les
épisodes par actif — il ne les propage simplement pas jusqu'aux euros.

### Le mécanisme proposé

1. Attribuer chaque incident simulé à l'actif dont l'épisode l'a engendré.
2. Pondérer la sévérité par un **multiplicateur de criticité** m(c), de sorte
   qu'une base de données de criticité 5 coûte plus cher qu'un poste de
   criticité 1.
3. Sortir un classement des actifs par perte annuelle attendue.

La contrainte à respecter : **la somme des allocations doit rester égale à
l'AAL**. On normalise donc :

$$\text{AAL}_{\text{actif } j} = \text{AAL} \times \frac{e_j \cdot m(c_j)}{\sum_k e_k \cdot m(c_k)}$$

où eⱼ est le nombre d'épisodes de l'actif j.

### Exemple chiffré

Trois actifs, AAL totale 273 704 € :

| actif | épisodes | criticité | multiplicateur |
|---|---:|---:|---:|
| A | 120 | 1 | 1,0 |
| B | 300 | 5 | 2,5 |
| C | 60 | 3 | 1,7 |

**Sans multiplicateur** (part proportionnelle aux seuls épisodes) :
```
total épisodes = 480
A : 120/480 = 25,0 %  →  68 426 €
B : 300/480 = 62,5 %  → 171 065 €
C :  60/480 = 12,5 %  →  34 213 €
```

**Avec multiplicateur :**
```
poids A = 120 × 1,0 = 120
poids B = 300 × 2,5 = 750
poids C =  60 × 1,7 = 102
total               = 972

A : 120/972 = 12,3 %  →  33 791 €
B : 750/972 = 77,2 %  → 211 191 €
C : 102/972 = 10,5 %  →  28 722 €

somme = 273 704 €  ✓ conservée
```

Le multiplicateur déplace 40 126 € de A et C vers B (34 635 € pris à A, 5 491 € à C). **C'est un montant réel
dans un rapport, produit par un nombre inventé** — d'où la difficulté.

### Pourquoi ce n'est pas fait

**Le multiplicateur serait inventé.** La base d'incidents enregistre des pertes
au niveau de l'entreprise, jamais au niveau de l'actif : rien n'y relie un coût
à une criticité. Toute courbe m(c) serait une hypothèse déguisée en mesure.

Pire, **les données refusent activement de la fournir** : la section 5 du
notebook constate que la sévérité est statistiquement indépendante de la
criticité dans la télémétrie — 26 à 27 % d'événements attack-grade à tous les
niveaux de criticité.

Il faut donc soit une source externe, soit une hypothèse **explicite et
étiquetée comme telle**. La seconde option est parfaitement acceptable en
mission ; ce qui ne l'est pas, c'est de la présenter comme un résultat.

---

# Partie III

## 15. Glossaire

| Terme | Définition courte |
|---|---|
| **AAL** | *Average Annual Loss*. L'espérance de la perte annuelle. |
| **AEP** | *Aggregate Exceedance Probability*. Probabilité que le **total** d'une année dépasse un montant. |
| **α (Pareto)** | Indice de queue, α = 1/ξ. α ≤ 1 ⇒ moyenne infinie ; α ≤ 2 ⇒ variance infinie. |
| **Attack-grade** | Événement de sévérité high ou critical — le sous-ensemble traité comme signal d'attaque. |
| **Bühlmann (crédibilité)** | Cadre actuariel exprimant une estimation comme Z·(observation) + (1−Z)·(a priori). |
| **Copule** | Fonction reliant des lois marginales à leur loi jointe ; isole la structure de dépendance. |
| **CRPS** | *Continuous Ranked Probability Score*. Règle de score propre pour prévision probabiliste ; se lit en euros. |
| **Écrêtage** | Remplacer X par min(X, C). Crée une masse ponctuelle en C. |
| **Épisode** | Une attaque reconstituée depuis ses alertes : événements attack-grade sur un actif, sans silence supérieur à la fenêtre de session. |
| **FAIR** | *Factor Analysis of Information Risk*. Ontologie décomposant le risque en TEF × Vulnérabilité × Magnitude. |
| **GPD** | *Generalized Pareto Distribution*. Loi limite des dépassements de seuil. |
| **Kish (n_eff)** | Taille d'échantillon effective, (Σw)²/Σw². Mesure la régularité des poids, pas leur taille. |
| **KS** | Kolmogorov–Smirnov. Écart vertical maximal entre répartitions empirique et théorique. |
| **λ (lambda)** | Taux du processus de Poisson : nombre moyen d'événements par unité de temps. |
| **LEF** | *Loss Event Frequency* (FAIR) = TEF × Vulnérabilité. Correspond à λ_incident. |
| **Lognormale** | Loi de X telle que ln X est normale. Médiane e^μ, moyenne e^(μ+σ²/2). |
| **Marginale** | Loi d'une variable prise isolément, sans référence aux autres. |
| **Mesure cohérente** | Mesure de risque monotone, sous-additive, homogène et invariante par translation. La TVaR l'est ; la VaR non. |
| **OEP** | *Occurrence Exceedance Probability*. Probabilité que la **plus grosse perte unitaire** d'une année dépasse un montant. |
| **PIT** | *Probability Integral Transform*. U = F(Y) est uniforme si F est la vraie loi. Diagnostic de calibration. |
| **Poisson composée** | Somme d'un nombre aléatoire (Poisson) de termes aléatoires i.i.d. |
| **POT** | *Peaks Over Threshold*. Méthode d'estimation de queue sur les dépassements d'un seuil. |
| **Prior conjugué** | A priori tel que le posterior appartient à la même famille. Gamma l'est pour Poisson. |
| **p_materialize** | Part des attaques détectées qui produisent une perte. Ici 1,946 × 10⁻⁴, soit 1 sur 5 138. |
| **Règle de score propre** | Règle optimisée en espérance par la vraie loi ; ne récompense pas le mensonge. |
| **Sous-additivité** | ρ(A+B) ≤ ρ(A) + ρ(B). Formalise « diversifier ne peut pas augmenter le risque ». |
| **TEF** | *Threat Event Frequency* (FAIR). Correspond à λ_détecté. |
| **Troncature** | Conditionner sur X < C et renormaliser. Ne crée pas d'atome. |
| **TVaR** | *Tail Value at Risk* = E[S | S ≥ VaR]. Aussi Expected Shortfall, CVaR. |
| **VaR** | *Value at Risk*. Quantile de la perte annuelle. |
| **ξ (xi)** | Paramètre de forme de la GPD. Contrôle entièrement la lourdeur de la queue. |
| **Z (crédibilité)** | Poids accordé à l'observation propre, Z = n/(n+k). |

---

## Pour aller plus loin

| Sujet | Référence |
|---|---|
| Crédibilité, Bühlmann–Straub | Bühlmann & Gisler, *A Course in Credibility Theory and its Applications* (2005) |
| Valeurs extrêmes, POT, GPD | Coles, *An Introduction to Statistical Modeling of Extreme Values* (2001) |
| Copules et dépendance | Embrechts, McNeil & Straumann, *Correlation and Dependence in Risk Management* (2002) |
| Mesures de risque cohérentes | Artzner, Delbaen, Eber & Heath, *Coherent Measures of Risk* (1999) |
| Scores propres, CRPS, PIT | Gneiting & Raftery, *Strictly Proper Scoring Rules, Prediction, and Estimation* (2007) |
| FAIR | Freund & Jones, *Measuring and Managing Information Risk: A FAIR Approach* (2014) |
| Risque agrégé, Poisson composée | Klugman, Panjer & Willmot, *Loss Models: From Data to Decisions* (5ᵉ éd., 2019) |

---

Les décisions de modélisation effectivement prises dans ce projet — et leurs
justifications — sont dans [`METHODOLOGY.md`](METHODOLOGY.md). Les arbitrages de
ce qui n'a pas été fait sont dans [`next_steps.md`](next_steps.md). La page
`/roadmap` de l'interface présente les mêmes chantiers sous forme de frise.
