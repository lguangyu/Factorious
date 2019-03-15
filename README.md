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

This is a `back end` of Factorio calculators, which means it mostly solves the
tedious calculations but only has a simple (and ugly) front end for input and
visualization. Some specific goals achieved by this calculator are:

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


### What issues this calculator has not addressed yet:

This calculator, as so far, is far from perfect. Some of the knowns issues are:

* Module/beacons. This is important as modules modifies the yielding ratio.
Should be solved in next major update.
* Mining cost. All mining costs are currently not included.
* Power consumption. Power is important, while it can be easily solved by the
front end in analogy of unit conversion. This feature likely will not be included
in this back end, which is designed to be abstract.
* Arbitrary precision calculation. Precision loss is innevitable when using bare
float number calculations. However, it only has notable impacts when user inputs
are in infeasibly large or small quantaties (e.g. build a million trillions of
`rocket-parts` per minute, or aiming at complete something within period of time
comparable to that since the biginning of the universe).
