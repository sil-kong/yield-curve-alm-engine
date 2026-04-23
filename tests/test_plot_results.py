from yield_curve_alm_engine.scripts.plot_results import parse_args


def test_plot_results_show_flag_is_opt_in() -> None:
    assert parse_args([]).show is False
    assert parse_args(["--show"]).show is True
