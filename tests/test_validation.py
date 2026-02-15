"""Tests for feature validation in PredictionRequest schema."""

import math
import pytest
from src.inference_server.schemas import PredictionRequest


class TestNaNInfReplacement:
    def test_nan_replaced_with_zero(self):
        req = PredictionRequest(flow_duration=float("nan"))
        assert req.flow_duration == 0.0

    def test_inf_replaced_with_zero(self):
        req = PredictionRequest(flow_duration=float("inf"))
        assert req.flow_duration == 0.0

    def test_negative_inf_replaced_with_zero(self):
        req = PredictionRequest(flow_duration=float("-inf"))
        assert req.flow_duration == 0.0

    def test_normal_value_unchanged(self):
        req = PredictionRequest(flow_duration=42.5)
        assert req.flow_duration == 42.5


class TestNonNegativeClamping:
    def test_negative_packet_count_clamped(self):
        req = PredictionRequest(tot_fwd_pkts=-5.0)
        assert req.tot_fwd_pkts == 0.0
        assert any("tot_fwd_pkts" in w for w in req._validation_warnings)

    def test_negative_flow_duration_clamped(self):
        req = PredictionRequest(flow_duration=-100.0)
        assert req.flow_duration == 0.0

    def test_zero_is_valid(self):
        req = PredictionRequest(tot_fwd_pkts=0.0)
        assert req.tot_fwd_pkts == 0.0

    def test_positive_unchanged(self):
        req = PredictionRequest(tot_fwd_pkts=10.0)
        assert req.tot_fwd_pkts == 10.0


class TestFlagClamping:
    def test_flag_above_one_clamped(self):
        req = PredictionRequest(syn_flag_cnt=5.0)
        assert req.syn_flag_cnt == 1.0
        assert any("syn_flag_cnt" in w for w in req._validation_warnings)

    def test_flag_negative_clamped(self):
        req = PredictionRequest(fin_flag_cnt=-1.0)
        assert req.fin_flag_cnt == 0.0

    def test_flag_valid_zero(self):
        req = PredictionRequest(ack_flag_cnt=0.0)
        assert req.ack_flag_cnt == 0.0

    def test_flag_valid_one(self):
        req = PredictionRequest(ack_flag_cnt=1.0)
        assert req.ack_flag_cnt == 1.0


class TestCleanInput:
    def test_no_warnings_on_clean_input(self):
        req = PredictionRequest(
            flow_duration=100.0,
            tot_fwd_pkts=10.0,
            syn_flag_cnt=1.0,
        )
        assert req._validation_warnings == []


class TestSrcIpNotAffected:
    def test_src_ip_passes_through(self):
        req = PredictionRequest(src_ip="192.168.1.1")
        assert req.src_ip == "192.168.1.1"

    def test_src_ip_none(self):
        req = PredictionRequest()
        assert req.src_ip is None
