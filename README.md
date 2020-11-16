[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]


# SNDPgen

Generator of Stochastic Network Design Problems (SNDP) in .mps and .mps formats.


<!-- <a href="https://github.com/pashtetgp/sndpgen">View Demo</a> -->
[Report Bug](https://github.com/pashtetgp/sndpgen/issues)
    -
[Request Feature](https://github.com/pashtetgp/sndpgen/issues)



<!-- TABLE OF CONTENTS -->
## Table of Contents

* [Problem description](#problem-description)
  * [Built With](#built-with)
* [Getting Started](#getting-started)
  * [Prerequisites](#prerequisites)
  * [Installation](#installation)
* [Usage](#usage)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)
* [Acknowledgements](#acknowledgements)



<!-- ABOUT THE PROJECT -->
## Problem description

![Model def](https://github.com/pashtetGP/sndpgen/raw/master/model_def.png)

In every location _L\\{m}_ a company produces some of the intermediate products _P\\{e}_.
For the production of an end product _e in P_ locations _F subset of L_ are possible.
The construction of a production line for end product _e_ with a capacity of _u_ units costs _f_.
In addition, for every possible route _(i,j) in A_, arise the delivery cost _c_ij_ per product unit.
An estimated _d_ units of product _e_ can be delivered to the market location _m_ and sold for the price _a_ per unit.
Where should the production lines for the end product _e_ be set up to maximize the profit?

Deman _d_ is assumed to be stochastic.

Package can be used to generate the instances with the different amount of locations, products, and stochastic scenarios.

![Example](https://github.com/pashtetGP/sndpgen/raw/master/SNDP_10_5_0.jpg)

Above is the visualization of the instance with 10 locations and 5 products.
Products manufactured in every location are mentioned in the node captions.
Red node is the market, grey nodes are the locations with the end product (5).
Numbers near the arcs are the delivery costs.


### Built With

* [Python 3.6](https://www.python.org/)

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites
* Python 3.6
* pyyaml
* graphviz (optional, for visualization)
* [OptiMax Component Library](http://www.maximalsoftware.com/optimax/) (optional, for price _a_ adjustment)

### Installation

1. Clone the repo
    ```
    git clone https://github.com/pashtetgp/sndpgen.git
    ```
   
1. cd to project folder and install the package
    ```
    cd C:\CodingProjects\sndpgen
    pip install ..\sndpgen
    ```

### Graphviz Installation

- install the package with `pip install graphviz`
- download binaries 32 bit [here](https://graphviz.gitlab.io/_pages/Download/Download_windows.html)
- install them, e.g., here: C:\Program Files (x86)\Graphviz2.38\. Bins will be in folder C:\Program Files (x86)\Graphviz2.38\bin
- edit system env vars: to System path append bins folder
- restart pc

### Uninstall

Run in command line `pip uninstall sndpgen`

<!-- USAGE EXAMPLES -->
## Usage

- Create a 'param.yaml' file and specify the number locations, number products and number scenarios in new instances.
Instances with all possible combinations of parameters will be generated.

In addition, multiple instance variations for each parameter combination can be generated.
Variations for the same parameters in parameter combination differ by delivery costs between locations and other values.
Technically different random seed is used for each parameter combination. E.g.,

<pre>
num_locations:
    - 10
    - 20
    - 40
num_products:
    - 5
    - 10
    - 20
num_scen:
    - 1
    - 25
    - 125
    - 500
    - 1000
    - 10000
num_variations: 3 #create 3 variations for each combination
</pre>

- cd to project folder, e.g., `cd C:\CodingProjects\sndp`

- run `sndp_gen`. This command accepts one argument `--yaml` - .yaml file with the parameters of SNDP problems to generate. Default: param.yaml

<!-- ROADMAP -->
## Roadmap

See the [open issues](https://github.com/pashtetgp/sndpgen/issues) for a list of proposed features (and known issues).



<!-- CONTRIBUTING -->
## Contributing

Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact

Pavlo Glushko

Project Link: [https://github.com/pashtetgp/sndpgen](https://github.com/pashtetgp/sndpgen)


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/pashtetgp/sndpgen.svg?style=flat-square
[contributors-url]: https://github.com/pashtetgp/sndpgen/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/pashtetgp/sndpgen.svg?style=flat-square
[forks-url]: https://github.com/pashtetgp/sndpgen/network/members
[stars-shield]: https://img.shields.io/github/stars/pashtetgp/sndpgen.svg?style=flat-square
[stars-url]: https://github.com/pashtetgp/sndpgen/stargazers
[issues-shield]: https://img.shields.io/github/issues/pashtetgp/sndpgen.svg?style=flat-square
[issues-url]: https://github.com/pashtetgp/sndpgen/issues
[license-shield]: https://img.shields.io/github/license/pashtetgp/sndpgen.svg?style=flat-square
[license-url]: https://github.com/pashtetgp/sndpgen/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/pavloglushko