#
# Simulations: discharge of a lead-acid battery
#
import argparse
import matplotlib.pyplot as plt
import numpy as np
import pickle
import pybamm
from config import OUTPUT_DIR
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from shared import model_comparison, convergence_study


def plot_voltages(all_variables, t_eval, Crates):
    # Only use some Crates
    all_variables = {k: v for k, v in all_variables.items() if k in Crates}
    # Plot
    plt.subplots()
    n = int(len(all_variables) // np.sqrt(len(all_variables)))
    m = np.ceil(len(all_variables) / n)
    for k, (Crate, models_variables) in enumerate(all_variables.items()):
        t_max = max(
            np.nanmax(var["Time [s]"](t_eval)) for var in models_variables.values()
        )
        ax = plt.subplot(n, m, k + 1)
        plt.axis([0, t_max, 10.5, 13])
        ax.set_xlabel("Time [s]")
        if len(Crates) > 1:
            plt.title("\\textbf{{({})}} {} C".format(chr(97 + k), Crate), y=-0.4)

        # Hide the right and top spines
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)

        # Only show ticks on the left and bottom spines
        ax.yaxis.set_ticks_position("left")
        ax.xaxis.set_ticks_position("bottom")

        # Add inset plot
        inset = inset_axes(ax, width="40%", height="40%", loc=1, borderpad=2)

        # Linestyles
        linestyles = ["k-", "b-.", "r--"]
        for j, (model_name, variables) in enumerate(models_variables.items()):
            if k == 0:
                label = model_name
            else:
                label = None
            if k % m == 0:
                ax.set_ylabel("Voltage [V]")

            ax.plot(
                variables["Time [s]"](t_eval),
                variables["Terminal voltage [V]"](t_eval) * 6,
                linestyles[j],
                label=label,
            )
            inset.plot(
                variables["Time [s]"](t_eval[:40]),
                variables["Terminal voltage [V]"](t_eval[:40]) * 6,
                linestyles[j],
            )
        # plt.legend(loc="upper right")
    file_name = "capacitance_voltage_comparison.eps".format(Crate)
    plt.show()
    # plt.savefig(OUTPUT_DIR + file_name, format="eps", dpi=1000)


def plot_errors(all_variables, t_eval, Crates):
    def rmse(predictions, targets):
        return np.sqrt(np.nanmean((predictions - targets) ** 2))

    # Only use some Crates
    all_variables = {k: v for k, v in all_variables.items() if k in Crates}
    # Plot
    plt.subplots()
    for k, (Crate, models_variables) in enumerate(all_variables.items()):
        ax = plt.subplot(1, 1, 1)
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Error [V]")

        # Hide the right and top spines
        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)

        # Only show ticks on the left and bottom spines
        ax.yaxis.set_ticks_position("left")
        ax.xaxis.set_ticks_position("bottom")

        # Linestyles
        linestyles = ["k-", "b-.", "r--"]

        for j, (model, variables) in enumerate(models_variables.items()):
            options = dict(model[1])
            if options["capacitance"] is False:
                base_model_results = models_variables[model]
                continue
            if k == 0:
                label = model[0]
            else:
                label = None

            error = np.abs(
                variables["Terminal voltage [V]"](t_eval)
                - base_model_results["Terminal voltage [V]"](t_eval)
            )
            ax.loglog(variables["Time [s]"](t_eval), error, linestyles[j], label=label)
        # plt.legend(loc="upper right")
    file_name = "capacitance_errors_voltages.eps".format(Crate)
    plt.show()
    # plt.savefig(OUTPUT_DIR + file_name, format="eps", dpi=1000)


def compare_voltages(args, models):
    t_eval = np.concatenate([np.logspace(-6, -3, 50), np.linspace(0.001, 1, 100)[1:]])
    if args.compute:
        Crates = [2]  # , 0.5, 1, 2]
        all_variables, t_eval = model_comparison(models, Crates, t_eval)
        with open("capacitance_data.pickle", "wb") as f:
            data = (all_variables, t_eval)
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    with open("capacitance_data.pickle", "rb") as f:
        (all_variables, t_eval) = pickle.load(f)
    plot_voltages(all_variables, t_eval, Crates)
    plot_errors(all_variables, t_eval, Crates)


def convergence_studies(args, models):
    t_eval = np.concatenate([np.logspace(-6, -3, 50), np.linspace(0.001, 1, 100)[1:]])
    all_npts = [10, 30, 50]
    if args.compute:
        all_variables, t_eval = convergence_study(models, 1, t_eval, all_npts)
        with open("capacitance_convergence_study.pickle", "wb") as f:
            data = (all_variables, t_eval)
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    with open("capacitance_convergence_study.pickle", "rb") as f:
        (all_variables, t_eval) = pickle.load(f)
    all_times = {
        model: [
            [x for x in all_variables[npts].values()][i]["solution"].solve_time
            for npts in all_npts
        ]
        for i, model in enumerate(models)
    }
    fig, ax = plt.subplots()
    linestyles = ["k-", "b-.", "r--"]
    labels = [
        "Direct formulation",
        "Capacitance formulation (differential)",
        "Capacitance formulation (algebraic)",
    ]
    for j, times in enumerate(all_times.values()):
        ax.loglog(all_npts, times, linestyles[j], label=labels[j])
    ax.set_xlabel("Number of grid points")
    ax.set_ylabel("Time [s]")
    ax.legend()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compute", action="store_true", help="(Re)-compute results.")
    args = parser.parse_args()
    pybamm.set_logging_level("INFO")
    models = [
        pybamm.lead_acid.NewmanTiedemann(),
        pybamm.lead_acid.NewmanTiedemann({"capacitance": "differential"}),
        pybamm.lead_acid.NewmanTiedemann({"capacitance": "algebraic"}),
    ]
    # compare_voltages(args, models)
    convergence_studies(args, models)
