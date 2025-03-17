from study_lyte.adjustments import merge_on_to_time
import logging

LOG = logging.getLogger(__name__)

def build_high_resolution_data(raw_sensor, baro_depth, acceleration, log):
    """
    Grabs the bottom sensors (sampled at the highest rate) then grabs the supporting sensors
    and pads with nans to fit into the same dataframe

    Args:
        cli: Instantiated Radicl() class
        log: Instantiated logger object

    Returns:
        result: Single data frame containing Force, NIR, Ambient NIR, Accel, Depth
    """
    LOG.info("Building High resolution profile...")
    # Invert Depth so bottom is negative max depth
    baro_depth['depth'] = baro_depth['filtereddepth'] - baro_depth['filtereddepth'].max()
    baro_depth = baro_depth.drop(columns=['filtereddepth'])

    log.info("Barometer Depth achieved: {:0.1f} cm".format(abs(baro_depth['depth'].max() - baro_depth['depth'].min())))
    log.info("Barometer Samples: {:,}".format(len(baro_depth.index)))
    log.info("Acceleration Samples: {:,}".format(len(acceleration.index)))
    log.info("Sensor Samples: {:,}".format(len(raw_sensor)))

    log.info("Infilling and interpolating dataset...")
    result = merge_on_to_time([raw_sensor, baro_depth, acceleration], raw_sensor.index)
    return result
