from pydantic import BaseModel, Field
from typing import Optional

class PredictionRequest(BaseModel):
    """
    Pydantic model for prediction request features.
    Defaults are set to 0.0 to allow partial updates and backward compatibility,
    but types are strictly enforced.
    """
    flow_duration: float = Field(0.0, alias="flow_duration")
    tot_fwd_pkts: float = Field(0.0, alias="tot_fwd_pkts")
    tot_bwd_pkts: float = Field(0.0, alias="tot_bwd_pkts")
    totlen_fwd_pkts: float = Field(0.0, alias="totlen_fwd_pkts")
    totlen_bwd_pkts: float = Field(0.0, alias="totlen_bwd_pkts")
    fwd_pkt_len_max: float = Field(0.0, alias="fwd_pkt_len_max")
    fwd_pkt_len_min: float = Field(0.0, alias="fwd_pkt_len_min")
    fwd_pkt_len_mean: float = Field(0.0, alias="fwd_pkt_len_mean")
    fwd_pkt_len_std: float = Field(0.0, alias="fwd_pkt_len_std")
    bwd_pkt_len_max: float = Field(0.0, alias="bwd_pkt_len_max")
    bwd_pkt_len_min: float = Field(0.0, alias="bwd_pkt_len_min")
    bwd_pkt_len_mean: float = Field(0.0, alias="bwd_pkt_len_mean")
    bwd_pkt_len_std: float = Field(0.0, alias="bwd_pkt_len_std")
    flow_byts_s: float = Field(0.0, alias="flow_byts_s")
    flow_pkts_s: float = Field(0.0, alias="flow_pkts_s")
    flow_iat_mean: float = Field(0.0, alias="flow_iat_mean")
    flow_iat_std: float = Field(0.0, alias="flow_iat_std")
    flow_iat_max: float = Field(0.0, alias="flow_iat_max")
    flow_iat_min: float = Field(0.0, alias="flow_iat_min")
    fwd_iat_tot: float = Field(0.0, alias="fwd_iat_tot")
    fwd_iat_mean: float = Field(0.0, alias="fwd_iat_mean")
    fwd_iat_std: float = Field(0.0, alias="fwd_iat_std")
    fwd_iat_max: float = Field(0.0, alias="fwd_iat_max")
    fwd_iat_min: float = Field(0.0, alias="fwd_iat_min")
    bwd_iat_tot: float = Field(0.0, alias="bwd_iat_tot")
    bwd_iat_mean: float = Field(0.0, alias="bwd_iat_mean")
    bwd_iat_std: float = Field(0.0, alias="bwd_iat_std")
    bwd_iat_max: float = Field(0.0, alias="bwd_iat_max")
    bwd_iat_min: float = Field(0.0, alias="bwd_iat_min")
    fwd_psh_flags: float = Field(0.0, alias="fwd_psh_flags")
    bwd_psh_flags: float = Field(0.0, alias="bwd_psh_flags")
    fwd_urg_flags: float = Field(0.0, alias="fwd_urg_flags")
    bwd_urg_flags: float = Field(0.0, alias="bwd_urg_flags")
    fwd_header_len: float = Field(0.0, alias="fwd_header_len")
    bwd_header_len: float = Field(0.0, alias="bwd_header_len")
    fwd_pkts_s: float = Field(0.0, alias="fwd_pkts_s")
    bwd_pkts_s: float = Field(0.0, alias="bwd_pkts_s")
    pkt_len_min: float = Field(0.0, alias="pkt_len_min")
    pkt_len_max: float = Field(0.0, alias="pkt_len_max")
    pkt_len_mean: float = Field(0.0, alias="pkt_len_mean")
    pkt_len_std: float = Field(0.0, alias="pkt_len_std")
    pkt_len_var: float = Field(0.0, alias="pkt_len_var")
    fin_flag_cnt: float = Field(0.0, alias="fin_flag_cnt")
    syn_flag_cnt: float = Field(0.0, alias="syn_flag_cnt")
    rst_flag_cnt: float = Field(0.0, alias="rst_flag_cnt")
    psh_flag_cnt: float = Field(0.0, alias="psh_flag_cnt")
    ack_flag_cnt: float = Field(0.0, alias="ack_flag_cnt")
    urg_flag_cnt: float = Field(0.0, alias="urg_flag_cnt")
    cwr_flag_count: float = Field(0.0, alias="cwr_flag_count")
    ece_flag_cnt: float = Field(0.0, alias="ece_flag_cnt")
    down_up_ratio: float = Field(0.0, alias="down_up_ratio")
    pkt_size_avg: float = Field(0.0, alias="pkt_size_avg")
    fwd_seg_size_avg: float = Field(0.0, alias="fwd_seg_size_avg")
    bwd_seg_size_avg: float = Field(0.0, alias="bwd_seg_size_avg")
    fwd_byts_b_avg: float = Field(0.0, alias="fwd_byts_b_avg")
    fwd_pkts_b_avg: float = Field(0.0, alias="fwd_pkts_b_avg")
    fwd_blk_rate_avg: float = Field(0.0, alias="fwd_blk_rate_avg")
    bwd_byts_b_avg: float = Field(0.0, alias="bwd_byts_b_avg")
    bwd_pkts_b_avg: float = Field(0.0, alias="bwd_pkts_b_avg")
    bwd_blk_rate_avg: float = Field(0.0, alias="bwd_blk_rate_avg")
    subflow_fwd_pkts: float = Field(0.0, alias="subflow_fwd_pkts")
    subflow_fwd_byts: float = Field(0.0, alias="subflow_fwd_byts")
    subflow_bwd_pkts: float = Field(0.0, alias="subflow_bwd_pkts")
    subflow_bwd_byts: float = Field(0.0, alias="subflow_bwd_byts")
    init_fwd_win_byts: float = Field(0.0, alias="init_fwd_win_byts")
    init_bwd_win_byts: float = Field(0.0, alias="init_bwd_win_byts")
    fwd_act_data_pkts: float = Field(0.0, alias="fwd_act_data_pkts")
    fwd_seg_size_min: float = Field(0.0, alias="fwd_seg_size_min")
    active_mean: float = Field(0.0, alias="active_mean")
    active_std: float = Field(0.0, alias="active_std")
    active_max: float = Field(0.0, alias="active_max")
    active_min: float = Field(0.0, alias="active_min")
    idle_mean: float = Field(0.0, alias="idle_mean")
    idle_std: float = Field(0.0, alias="idle_std")
    idle_max: float = Field(0.0, alias="idle_max")
    idle_min: float = Field(0.0, alias="idle_min")
    
    # Optional metadata for observability
    src_ip: Optional[str] = Field(None, alias="src_ip")

    class Config:
        populate_by_name = True


# Alert and Incident Schemas

class AlertResponse(BaseModel):
    """Response model for Alert"""
    id: int
    attack_type: str
    severity: str
    src_ip: str
    dst_ip: Optional[str]
    timestamp: str
    prediction_score: Optional[float]
    acknowledged: bool
    incident_id: Optional[int]
    notes: Optional[str]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "attack_type": "DDoS",
                "severity": "high",
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.50",
                "timestamp": "2025-12-02T20:00:00",
                "prediction_score": 0.95,
                "acknowledged": False,
                "incident_id": None,
                "notes": None
            }
        }


class AlertUpdate(BaseModel):
    """Request model for updating an alert"""
    acknowledged: Optional[bool] = None
    notes: Optional[str] = None


class IncidentResponse(BaseModel):
    """Response model for Incident"""
    id: int
    title: str
    description: Optional[str]
    status: str
    severity: str
    assigned_to: Optional[str]
    created_at: str
    updated_at: str
    resolved_at: Optional[str]
    notes: Optional[str]
    
    class Config:
        from_attributes = True


class IncidentCreate(BaseModel):
    """Request model for creating an incident"""
    title: str
    description: Optional[str] = None
    status: Optional[str] = "open"
    severity: Optional[str] = "medium"
    assigned_to: Optional[str] = None


class IncidentUpdate(BaseModel):
    """Request model for updating an incident"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None
