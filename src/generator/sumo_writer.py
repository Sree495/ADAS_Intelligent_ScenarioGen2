"""
generator/sumo_writer.py
------------------------
Writes SUMO network (.net.xml), route (.rou.xml), gui settings (.view.xml)
and config (.sumocfg) files for a concrete scenario.
"""
from __future__ import annotations
from pathlib import Path
import textwrap

from src.generator.variation_engine import ConcreteScenario


SCENARIOS_DIR = Path(__file__).parents[2] / "data" / "scenarios"
SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)


def write_straight_network(scenario: ConcreteScenario) -> Path:
    is_oncoming = scenario.target_motion in ("oncoming", "oncoming_lane_change")

    if is_oncoming:
        net_xml = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <net version="1.16" junctionCornerDetail="5" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

            <location netOffset="0.00,0.00" convBoundary="0.00,0.00,500.00,10.50"
                      origBoundary="-180.00,-90.00,180.00,90.00" projParameter="!"/>

            <edge id="road_fwd" from="node_start" to="node_end" priority="-1">
                <lane id="road_fwd_0" index="0" speed="36.11" length="500.00" width="3.50"
                      shape="0.00,1.75 500.00,1.75"/>
            </edge>

            <edge id="road_rev" from="node_end" to="node_start" priority="-1">
                <lane id="road_rev_0" index="0" speed="36.11" length="500.00" width="3.50"
                      shape="500.00,5.25 0.00,5.25"/>
            </edge>

            <junction id="node_start" type="dead_end" x="0.00" y="0.00"
                      incLanes="road_rev_0" intLanes="" shape="0.00,7.00 0.00,3.50"/>
            <junction id="node_end" type="dead_end" x="500.00" y="0.00"
                      incLanes="road_fwd_0" intLanes="" shape="500.00,0.00 500.00,3.50"/>

        </net>
        """)
    else:
        net_xml = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <net version="1.16" junctionCornerDetail="5" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

            <location netOffset="0.00,0.00" convBoundary="0.00,0.00,500.00,10.50"
                      origBoundary="-180.00,-90.00,180.00,90.00" projParameter="!"/>

            <edge id="road" from="node_start" to="node_end" priority="-1">
                <lane id="road_0" index="0" speed="36.11" length="500.00" width="3.50"
                      shape="0.00,1.75 500.00,1.75"/>
                <lane id="road_1" index="1" speed="36.11" length="500.00" width="3.50"
                      shape="0.00,5.25 500.00,5.25"/>
            </edge>

            <junction id="node_start" type="dead_end" x="0.00" y="0.00"
                      incLanes="" intLanes="" shape="0.00,3.50 0.00,-0.00"/>
            <junction id="node_end" type="dead_end" x="500.00" y="0.00"
                      incLanes="road_0 road_1" intLanes="" shape="500.00,-0.00 500.00,3.50"/>

        </net>
        """)
    out_path = SCENARIOS_DIR / f"{scenario.scenario_id}.net.xml"
    out_path.write_text(net_xml, encoding="utf-8")
    return out_path


def write_route_file(scenario: ConcreteScenario) -> Path:
    ego_speed_ms    = scenario.ego_speed_kmh / 3.6
    target_speed_ms = scenario.target_speed_kmh / 3.6
    friction        = scenario.friction_coeff
    max_decel       = round(9.0 * friction, 2)

    is_oncoming = scenario.target_motion in ("oncoming", "oncoming_lane_change")

    if is_oncoming:
        # Ego departs at x=50 on road_fwd (forward direction).
        # Target departs at pos=50 on road_rev, which corresponds to
        # absolute x ≈ 450 (500 - 50), travelling toward ego.
        rou_xml = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

            <!-- Scenario: {scenario.scenario_id} -->
            <!-- Family:   {scenario.family} -->
            <!-- Weather:  {scenario.weather}  |  Friction: {friction} -->
            <!-- SUT:      {scenario.sut_version} -->

            <vType id="ego_type" accel="3.0" decel="{max_decel}" sigma="0.0"
                   length="4.5" maxSpeed="55.56" speedFactor="1.0"
                   color="0,0,255"/>

            <vType id="target_type" accel="3.0" decel="{max_decel}" sigma="0.0"
                   length="4.5" maxSpeed="55.56" speedFactor="1.0"
                   color="255,0,0"/>

            <route id="route_ego"    edges="road_fwd"/>
            <route id="route_target" edges="road_rev"/>

            <vehicle id="ego" type="ego_type" route="route_ego"
                     depart="0.0" departPos="50.0"
                     departSpeed="{ego_speed_ms:.2f}" departLane="0"/>

            <vehicle id="target" type="target_type" route="route_target"
                     depart="0.0" departPos="50.0"
                     departSpeed="{target_speed_ms:.2f}" departLane="0"/>

        </routes>
        """)
    else:
        ego_depart_pos    = 50.0
        target_depart_pos = 250.0

        if scenario.target_motion == "stationary":
            target_speed_line = 'speed="0.00"'
        else:
            target_speed_line = f'speed="{target_speed_ms:.2f}"'

        rou_xml = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

            <!-- Scenario: {scenario.scenario_id} -->
            <!-- Family:   {scenario.family} -->
            <!-- Weather:  {scenario.weather}  |  Friction: {friction} -->
            <!-- SUT:      {scenario.sut_version} -->

            <vType id="ego_type" accel="3.0" decel="{max_decel}" sigma="0.0"
                   length="4.5" maxSpeed="55.56" speedFactor="1.0"
                   color="0,0,255"/>

            <vType id="target_type" accel="3.0" decel="{max_decel}" sigma="0.0"
                   length="4.5" maxSpeed="55.56" speedFactor="1.0"
                   color="255,0,0"/>

            <route id="route_ego"    edges="road"/>
            <route id="route_target" edges="road"/>

            <vehicle id="ego" type="ego_type" route="route_ego"
                     depart="0.0" departPos="{ego_depart_pos:.1f}"
                     departSpeed="{ego_speed_ms:.2f}" departLane="0"/>

            <vehicle id="target" type="target_type" route="route_target"
                     depart="0.0" departPos="{target_depart_pos:.1f}"
                     {target_speed_line} departLane="0"/>

        </routes>
        """)
    out_path = SCENARIOS_DIR / f"{scenario.scenario_id}.rou.xml"
    out_path.write_text(rou_xml, encoding="utf-8")
    return out_path


def write_gui_settings(scenario: ConcreteScenario) -> Path:
    """
    Writes gui-settings.xml so SUMO-GUI opens with:
      - Camera zoomed and centred between the two vehicles
      - Vehicles drawn 5x larger (visible at reasonable zoom)
      - Road dark grey on light background
      - Collision highlight enabled
    """
    view_xml = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <viewsettings>

        <!-- Zoom centred between ego (x=50) and target (x=250), y=1.75 (lane centre) -->
        <viewport x="150.00" y="1.75" zoom="600.00"/>
        <delay value="80"/>

        <scheme name="ADAS_Scenario">
            <background backgroundColor="230,230,230" showGrid="0"/>

            <edges laneEdgeMode="0" scaleSize="1"
                   showLinkDecals="1" showRails="0"
                   hideConnectors="0" widthExaggeration="2.0">
                <colorScheme name="uniform">
                    <entry color="50,50,50" name="road"/>
                </colorScheme>
            </edges>

            <vehicles vehicleMode="0" vehicleQuality="2"
                      minVehicleSize="6.0"
                      vehicleExaggeration="5.0"
                      showBlinker="1" drawMinGap="1"
                      scaleSize="1">
                <colorScheme name="given/assigned vehicle color">
                    <entry color="0,0,200"/>
                </colorScheme>
            </vehicles>

        </scheme>
    </viewsettings>
    """)
    out_path = SCENARIOS_DIR / f"{scenario.scenario_id}.view.xml"
    out_path.write_text(view_xml, encoding="utf-8")
    return out_path


def write_sumo_config(scenario: ConcreteScenario, net_path: Path, rou_path: Path) -> Path:
    fcd_output = SCENARIOS_DIR / f"{scenario.scenario_id}.fcd.xml"
    gui_path   = write_gui_settings(scenario)

    cfg_xml = textwrap.dedent(f"""\
    <?xml version="1.0" encoding="UTF-8"?>
    <configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">

        <input>
            <net-file value="{net_path.name}"/>
            <route-files value="{rou_path.name}"/>
        </input>

        <time>
            <begin value="0"/>
            <end value="30"/>
            <step-length value="0.1"/>
        </time>

        <output>
            <fcd-output value="{fcd_output.name}"/>
            <fcd-output.geo value="false"/>
        </output>

        <processing>
            <collision.action value="warn"/>
            <collision.mingap-factor value="0"/>
        </processing>

        <gui_only>
            <gui-settings-file value="{gui_path.name}"/>
            <start value="0"/>
        </gui_only>

        <report>
            <verbose value="false"/>
            <no-step-log value="true"/>
        </report>

    </configuration>
    """)

    cfg_path = SCENARIOS_DIR / f"{scenario.scenario_id}.sumocfg"
    cfg_path.write_text(cfg_xml, encoding="utf-8")
    return cfg_path


def write_scenario_files(scenario: ConcreteScenario) -> Path:
    """Convenience: write all four files and return path to .sumocfg."""
    net_path = write_straight_network(scenario)
    rou_path = write_route_file(scenario)
    cfg_path = write_sumo_config(scenario, net_path, rou_path)
    return cfg_path
