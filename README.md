Factorious: Back end for Factorio calculator
============================================


Dependencies
------------

* Python >= 3.6.0
* Numpy (array manipulations)
* Scipy (linear programming back end)

*Python 3.6.0 is required for compatibility of some function notations*


Description
-----------

### What this calculator can do:

This is a `back end` of calculators, which means it mostly solves the tedious
calculations but only has a simple (and ugly) input and visualization front end.
The calculation goals achieved in this calculator is:

* Set intermediate item as input material. The calculator can be set using any
intermediate material as direct input; this is useful when designing modularized
factories.
* Arbitrary multi-splits recipes optimization. One of this example is base
module's oil processing recieps: in which an identical product can have multiple
sources and/or one recipe can have multiple products that divert into totally
different downstream factories. Those recipes/items are automatically identified
and optimized to the 'minimal `input` requirement'. In some other calculators,
this behavior is hard-coded to known recipe collections and might need update
the internal database everytime more such recipes are included.
* Cyclic identification and optimization. Again, from v0.15 `Factorio` contains
recipes that form cycles: a set of recipes in a way that if connect one recipe
with another who consumes all or part of its products, then the fianl recipe
will produce some inputs of the first one. A famous example is base module's
`uranium-fuel-cell` cycle. In this calculator, this cyclic dependecy is also
automatically detected. Keep in mind, this feature can be disabled manually.
* Customized optimization. Optimizer is designed to be robust with potential
uneven availability of different resources, and find a solution per case: oil,
coal or even water limitations, nothing has to be left behind.
* Recipe control. Which recipe to use/exclude is fully customizable. For example,
the user can force the optimizer using `coal-liquefaction`.


### What issues this calculator does not address:

This calculator will never be perfect. Some of not addressed issues are:

* Module/beacons. This is important as modules modifies the yielding ratio.
* Mining cost. All mining costs are currently not included.
* Power. The output of this back end is a table of recipes with how many times
they should be executed, regardless of the building to craft these items.
Features like power consumption can be easily implemented in front end, with an
analogy unit conversion in real-life calculations.
* Arbitrary precision calculation. Precision loss is innevitable when using bare
float number calculations. However, this only has notable impacts when input ratio
is infeasibly large or small (i.e. build a million trillions of `rocket-parts` per
minute or complete an `stack-inserter` since the biginning of the universe).

The motivation to abstract the back end partially lies in the flexibility in
future uses. From the point of view of a monkey working in bioinformatics, this
sort of calculation is extremely similar to dealing with large amount of
bio/chemical equations.
