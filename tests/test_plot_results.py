from yield_curve_alm_engine.scripts.plot_results import parse_args, publish_docs_figures


def test_plot_results_show_flag_is_opt_in() -> None:
    assert parse_args([]).show is False
    assert parse_args(["--show"]).show is True


def test_plot_results_publish_docs_figures_flag_is_opt_in() -> None:
    assert parse_args([]).publish_docs_figures is False
    assert parse_args(["--publish-docs-figures"]).publish_docs_figures is True


def test_publish_docs_figures_copies_selected_pngs(tmp_path) -> None:
    source = tmp_path / "outputs"
    target = tmp_path / "docs" / "figures"
    source.mkdir()
    (source / "surplus_by_scenario.png").write_bytes(b"fake-png")

    published = publish_docs_figures(
        source_dir=source,
        target_dir=target,
        figure_names=["surplus_by_scenario.png"],
    )

    assert published == [target / "surplus_by_scenario.png"]
    assert (target / "surplus_by_scenario.png").read_bytes() == b"fake-png"
