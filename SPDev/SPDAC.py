import numpy as np
import itertools
import uuid
from time import sleep as sleep_s
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.instrument.visa import VisaInstrument
from pyvisa.errors import VisaIOError
from qcodes.utils import validators
from typing import NewType, Tuple, Sequence, List, Dict, Optional
from packaging.version import parse
import abc

# Version 1.0.0
#
# Guiding principles for this driver for SPDev SPDAC
# -----------------------------------------------------
#
# 1. Each command should be self-contained, so
#
#        spdac.ch02.dc_constant_V(0.1)
#
#    should make sure that channel 2 is in the right mode for outputting
#    a constant voltage.
#
# 2. Numeric values should be in ISO units and/or their unit should be an
#    explicitly part of the function name, like above.  If the numeric is
#    a unit-less number, then prefixed by n_ like
#
#        spdac.n_channels()
#
# 3. Allocation of resources should be automated as much as possible,
#    preferably by python context managers that automatically clean up on exit.
#    Such context managers have a name with a '_Context' suffix.
#
# 4. Any generator should by default be set to start on the BUS trigger
#    (*TRG) so that it is possible to synchronise several generators without
#    further setup; which also eliminates the need for special cases for the
#    BUS trigger.


# Context manager hierarchy
# -------------------------
#
# _Channel_Context
#   _Dc_Context
#     Sweep_Context
#     List_Context
# Virtual_Sweep_Context
# Arrangement_Context
# SPDacTrigger_Context
#
# Calling close() on any context manager will clean up any triggers or
# markers that were set up by the context.  Use with-statements to
# have this done automatically.


pseudo_trigger_voltage = 5


def ints_to_comma_separated_list(array: Sequence[int]) -> str:
    return ','.join([str(x) for x in array])


def floats_to_comma_separated_list(array: Sequence[float]) -> str:
    rounded = [format(x, 'g') for x in array]
    return ','.join(rounded)


def comma_sequence_to_list(sequence: str) -> Sequence[str]:
    if not sequence:
        return []
    return [x.strip() for x in sequence.split(',')]


def comma_sequence_to_list_of_floats(sequence: str) -> Sequence[float]:
    if not sequence:
        return []
    return [float(x.strip()) for x in sequence.split(',')]


def diff_matrix(initial: Sequence[float],
                measurements: Sequence[Sequence[float]]) -> np.ndarray:
    """Subtract an array of measurements by an initial measurement
    """
    matrix = np.asarray(measurements)
    return matrix - np.asarray(list(itertools.repeat(initial, matrix.shape[1])))


def split_version_string_into_components(version: str) -> List[str]:
    return version.split('-')


"""External input trigger

There are four 3V3 non-isolated triggers on the back (1, 2, 3, 4).
"""
ExternalInput = NewType('ExternalInput', int)
# NewType declaration can check the input class


class SPDacTrigger_Context:
    """Internal Triggers with automatic deallocation

    This context manager wraps an already-allocated internal trigger number so
    that the trigger can be automatically reclaimed when the context exits.
    """

    def __init__(self, parent: 'SPDac', value: int):
        self._parent = parent
        self._value = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._parent.free_trigger(self)
        # Propagate exceptions
        return False

    def close(self) -> None:
        self.__exit__(None, None, None)

    @property
    def value(self) -> int:
        """internal SCPI trigger number"""
        return self._value


def _trigger_context_to_value(trigger: SPDacTrigger_Context) -> int:
    return trigger.value


# in our devive, we do not make trigger function yet
class SPDacExternalTrigger(InstrumentChannel):
    """External output trigger

    There are three 5V isolated triggers on the front (1, 2, 3) and two
    non-isolated 3V3 on the back (4, 5).
    """

    def __init__(self, parent: 'SPDac', name: str, external: int):
        super().__init__(parent, name)
        self.add_function(
            name='source_from_bus',
            call_cmd=f'outp:trig:sour {external},bus'
        )
        self.add_parameter(
            name='source_from_input',
            # Route external input to external output
            set_cmd='outp:trig:sour {0},ext{1}'.format(external, '{}'),
        )
        self.add_parameter(
            name='source_from_trigger',
            # Route internal trigger to external output
            set_parser=_trigger_context_to_value,
            set_cmd='outp:trig:sour {0},int{1}'.format(external, '{}'),
        )
        self.add_parameter(
            name='width_s',
            label='width',
            unit='s',
            set_cmd='outp:trig:widt {0},{1}'.format(external, '{}'),
            get_cmd=f'outp:trig:widt? {external}',
            get_parser=float
        )
        self.add_parameter(
            name='polarity',
            label='polarity',
            set_cmd='outp:trig:pol {0},{1}'.format(external, '{}'),
            get_cmd=f'outp:trig:pol? {external}',
            get_parser=str,
            vals=validators.Enum('inv', 'norm')
        )
        self.add_parameter(
            name='delay_s',
            label='delay',
            unit='s',
            set_cmd='outp:trig:del {0},{1}'.format(external, '{}'),
            get_cmd=f'outp:trig:del? {external}',
            get_parser=float
        )
        self.add_function(
            name='signal',
            call_cmd=f'outp:trig:sign {external}'
        )


class _Channel_Context(metaclass=abc.ABCMeta):

    def __init__(self, channel: 'SPDacChannel'):
        self._channel = channel

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Propagate exceptions
        return False

    @abc.abstractmethod
    def close(self) -> None:
        pass

    def allocate_trigger(self) -> SPDacTrigger_Context:
        """Allocate internal trigger

        Returns:
            SPDacTrigger_Context: Context that wraps the trigger
        """
        return self._channel._parent.allocate_trigger()

    @abc.abstractmethod
    def start_on(self, trigger: SPDacTrigger_Context) -> None:
        pass

    @abc.abstractmethod
    def start_once_on(self, trigger: SPDacTrigger_Context) -> None:
        pass

    @abc.abstractmethod
    def start_on_external(self, trigger: ExternalInput) -> None:
        pass

    @abc.abstractmethod
    def start_once_on_external(self, trigger: ExternalInput) -> None:
        pass

    @abc.abstractmethod
    def abort(self) -> None:
        pass

    def _write_channel(self, cmd: str) -> None:
        self._channel.write_channel(cmd)

    def _write_channel_floats(self, cmd: str, values: Sequence[float]) -> None:
        self._channel.write_channel_floats(cmd, values)

    def _ask_channel(self, cmd: str) -> str:
        return self._channel.ask_channel(cmd)

    def _channel_message(self, template: str) -> None:
        return self._channel._channel_message(template)


class _Dc_Context(_Channel_Context):

    def __init__(self, channel: 'SPDacChannel'):
        super().__init__(channel)
        self._write_channel('sour:dc:trig:sour {0},hold')
        self._trigger: Optional[SPDacTrigger_Context] = None
        self._marker_start: Optional[SPDacTrigger_Context] = None
        self._marker_end: Optional[SPDacTrigger_Context] = None
        self._marker_step_start: Optional[SPDacTrigger_Context] = None
        self._marker_step_end: Optional[SPDacTrigger_Context] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.abort()
        if self._trigger:
            self._channel._parent.free_trigger(self._trigger)
        if self._marker_start:
            self._channel._parent.free_trigger(self._marker_start)
            self._write_channel(f'sour:dc:mark:star {"{0}"},0')
            # Pairs the STARt marker of the DC generator on channel {channel} with internal trigger number 0.
        if self._marker_end:
            self._channel._parent.free_trigger(self._marker_end)
            self._write_channel(f'sour:dc:mark:end {"{0}"},0')
            # Pairs the END marker of the DC generator on channel {channel} with internal trigger number 0.
        if self._marker_step_start:
            self._channel._parent.free_trigger(self._marker_step_start)
            self._write_channel(f'sour:dc:mark:sst {"{0}"},0')
            # Pairs the SSTart marker of the DC generator on channel {channel} with internal trigger number 0.
        if self._marker_step_end:
            self._channel._parent.free_trigger(self._marker_step_end)
            self._write_channel(f'sour:dc:mark:send {"{0}"},0')
            # Pairs the SEND marker of the DC generator on channel {channel} with internal trigger number 0.
        # Always disable any triggering
        # It seems it wouldn't check whether the command is successed or not
        self._write_channel(f'sour:dc:trig:sour {"{0}"},imm')
        # Propagate exceptions
        return False

    def close(self) -> None:
        self.__exit__(None, None, None)

    def start_on(self, trigger: SPDacTrigger_Context) -> None:
        """Attach internal trigger to DC generator

        Args:
            trigger (SPDacTrigger_Context): trigger that will start DC
        """
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sour:dc:trig:sour {"{0}"},int{internal}')
        # Use internal trigger no.{internal} 
        self._make_ready_to_start()

    def start_once_on(self, trigger: SPDacTrigger_Context) -> None:
        """Attach internal one-shot trigger to DC generator

        Args:
            trigger (SPDacTrigger_Context): trigger that will start DC
        """
        self._trigger = trigger
        internal = _trigger_context_to_value(trigger)
        self._write_channel(f'sour:dc:trig:sour {"{0}"},int{internal}')
        # Use internal trigger no.{internal} 
        self._make_ready_to_start_once()

    def start_on_external(self, trigger: ExternalInput) -> None:
        """Attach external trigger to DC generator

        Args:
            trigger (ExternalInput): trigger that will start DC generator
        """
        self._trigger = None
        self._write_channel(f'sour:dc:trig:sour {"{0}"},ext{trigger}')
        # Use hardware trigger no.{trigger}
        self._make_ready_to_start()

    def start_once_on_external(self, trigger: ExternalInput) -> None:
        """Attach external one-shot trigger to DC generator

        Args:
            trigger (ExternalInput): trigger that will start DC generator
        """
        self._trigger = None
        self._write_channel(f'sour:dc:trig:sour {"{0}"},ext{trigger}')
        # Use hardware trigger no.{trigger}
        self._make_ready_to_start_once()

    def abort(self) -> None:
        """Abort any DC running generator on the channel
        """
        self._write_channel('sour:dc:abor {0}')
        # Stop the DC out {channel}

    def end_marker(self) -> SPDacTrigger_Context:
        """Internal trigger that will mark the end of the DC generator

        A new internal trigger is allocated if necessary.

        Returns:
            SPDacTrigger_Context: trigger that will mark the end
        """
        if not self._marker_end:
            self._marker_end = self.allocate_trigger()
        self._write_channel(f'sour:dc:mark:end {"{0}"},{self._marker_end.value}')
        # Pairs the END marker of the DC generator on channel {channel} with internal trigger number {self._marker_end.value}.
        return self._marker_end

    def start_marker(self) -> SPDacTrigger_Context:
        """Internal trigger that will mark the beginning of the DC generator

        A new internal trigger is allocated if necessary.

        Returns:
            SPDacTrigger_Context: trigger that will mark the beginning
        """
        if not self._marker_start:
            self._marker_start = self.allocate_trigger()
        self._write_channel(f'sour:dc:mark:star {"{0}"},{self._marker_start.value}')
        # Pairs the STARt marker of the DC generator on channel {channel} with internal trigger number {self._marker_start.value}.
        return self._marker_start

    def step_end_marker(self) -> SPDacTrigger_Context:
        """Internal trigger that will mark the end of each step

        A new internal trigger is allocated if necessary.

        Returns:
            SPDacTrigger_Context: trigger that will mark the end of each step
        """
        if not self._marker_step_end:
            self._marker_step_end = self.allocate_trigger()
        self._write_channel(f'sour:dc:mark:send {"{0}"},{self._marker_step_end.value}')
        # Pairs the SEND marker of the DC generator on channel {channel} with internal trigger number {self._marker_step_end.value}.
        return self._marker_step_end

    def step_start_marker(self) -> SPDacTrigger_Context:
        """Internal trigger that will mark the beginning of each step

        A new internal trigger is allocated if necessary.

        Returns:
            SPDacTrigger_Context: trigger that will mark the end of each step
        """
        if not self._marker_step_start:
            self._marker_step_start = self.allocate_trigger()
        self._write_channel(f'sour:dc:mark:sst {"{0}"},{self._marker_step_start.value}')
        # Pairs the SSTart marker of the DC generator on channel {channel} with internal trigger number {self._marker_step_start.value}.
        return self._marker_step_start

    def _set_delay(self, delay_s: float) -> None:
        self._write_channel(f'sour:dc:del {"{0}"},{delay_s}')
        # Makes the DC generator on channel {channel} start {delay_s} after being triggered.

    def _set_triggering(self) -> None:
        self._write_channel('sour:dc:trig:sour {0},bus')
        # sets the trigger source to BUS for the DC generator on ch.{channel}
        # BUS is the global trigger (*trg command)
        self._make_ready_to_start()

    def _start(self, description: str) -> None:
        if self._trigger:
            self._make_ready_to_start()
            return self._write_channel(f'tint {self._trigger.value}')
            # Fires internal trigger #{self._trigger.value} starting all DC wave generators
        self._switch_to_immediate_trigger()
        self._write_channel('sour:dc:init {0}')
        # Makes the DC generator on channel {channel} wait for a DC trigger event. As the trigger source is set to IMMediate(default), the generator will start when this command is issued.

    def _make_ready_to_start(self) -> None:
        self._write_channel('sour:dc:init:cont {0},on')
        # Makes the DC generator on channel {channel} start waiting for trigger events. After a completed trigger cycle the generator will wait for a new trigger event.

    def _make_ready_to_start_once(self) -> None:
        self._write_channel('sour:dc:init:cont {0},off')
        # CONTinous mode is swithed off

    def _switch_to_immediate_trigger(self) -> None:
        self._write_channel('sour:dc:init:cont {0},off')
        self._write_channel('sour:dc:trig:sour {0},imm')
        # (default) If INITiate:IMMediate is executed, a single trigger event will be processed immediately. Change the CONTinous mode into single trigger mode


# this function is important, need to be done
# it function seems to be done in the device side
class Sweep_Context(_Dc_Context):

    def __init__(self, channel: 'SPDacChannel', start_V: float, stop_V: float,
                 points: int, repetitions: int, dwell_s: float, delay_s: float,
                 backwards: bool, stepped: bool):
        self._repetitions = repetitions
        super().__init__(channel)
        channel.write_channel('sour:volt:mode {0},swe')
        # sets the DC generator to SWEop mode channel {channel}. Outputs a voltage sweep according to the SWEep subsystem settings.
        self._set_voltages(start_V, stop_V)
        channel.write_channel(f'sour:swe:poin {"{0}"},{points}')
        # sets the number of sweep points for ch.{channel} to {points}. There will be {points - 1} levels.
        self._set_generation_mode(stepped)
        channel.write_channel(f'sour:swe:dwel {"{0}"},{dwell_s}')
        # sets the sweep dwell time for channel {channel} to {dwell_s}.
        super()._set_delay(delay_s)
        self._set_direction(backwards)
        self._set_repetitions()
        self._set_triggering()

    def _set_voltages(self, start_V: float, stop_V: float):
        self._write_channel(f'sour:swe:star {"{0}"},{start_V}')
        # sets the SWEep start voltage to {start_V} on ch.{channel}.
        self._write_channel(f'sour:swe:stop {"{0}"},{stop_V}')
        # sets the SWEep stop voltage to {stop_V} on ch.{channel}.

    def _set_generation_mode(self, stepped: bool) -> None:
        if stepped:
            return self._write_channel('sour:swe:gen {0},step')
            # sets the SWEep type to be a stair case for channel {channel}.
        self._write_channel('sour:swe:gen {0},anal')
        # sets the SWEep type to be a linear ramp for channel {channel}.

    # def _set_direction(self, backwards: bool) -> None:
    #     if backwards:
    #         return self._write_channel('sour:swe:dir {0},down')
    #         # ? command doesn't exist
    #     self._write_channel('sour:swe:dir {0} up')
    #     # ? command doesn't exist

    def _set_repetitions(self) -> None:
        self._write_channel(f'sour:swe:coun {"{0}"} {self._repetitions}')
        # sets the number of repetitions to {self._repetitions} for the sweep

    def _perpetual(self) -> bool:
        return self._repetitions < 0

    def start(self) -> None:
        """Start the DC sweep
        """
        self._start('DC sweep')
        # start generator function

    def points(self) -> int:
        """
        Returns:
            int: Number of steps in the DC sweep
        """
        return int(self._ask_channel('sour:swe:poin? {0}'))

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the DC sweep
        """
        return int(self._ask_channel('sour:swe:ncl? {0}'))

    def time_s(self) -> float:
        """
        Returns:
            float: Seconds that it will take to do the sweep
        """
        return float(self._ask_channel('sour:swe:time? {0}'))

    def start_V(self) -> float:
        """
        Returns:
            float: Starting voltage
        """
        return float(self._ask_channel('sour:swe:star? {0}'))

    def stop_V(self) -> float:
        """
        Returns:
            float: Ending voltage
        """
        return float(self._ask_channel('sour:swe:stop? {0}'))

    def values_V(self) -> Sequence[float]:
        """
        Returns:
            Sequence[float]: List of voltages
        """
        return list(np.linspace(self.start_V(), self.stop_V(), self.points()))
        # this function is done in local machine, not the actual volt for device


# this function doesn't need to support, will delete in next modification
class List_Context(_Dc_Context):

    def __init__(self, channel: 'SPDacChannel', voltages: Sequence[float],
                 repetitions: int, dwell_s: float, delay_s: float,
                 backwards: bool, stepped: bool):
        super().__init__(channel)
        self._repetitions = repetitions
        self._write_channel('sour:volt:mode {0},list')
        # sets the DC generator to LIST mode channel {channel}. Outputs a voltage sequence according to the LIST subsystem settings.
        self._set_voltages(voltages)
        self._set_trigger_mode(stepped)
        self._write_channel(f'sour:list:dwel {"{0}"},{dwell_s}')
        # sets the list dwell time for channel {channel} to {dwell_s}.
        super()._set_delay(delay_s)
        self._set_direction(backwards)
        self._set_repetitions()
        self._set_triggering()

    def _set_voltages(self, voltages: Sequence[float]) -> None:
        self._write_channel_floats('sour:list:volt {0},', voltages)
        # e.p. SOUR1:LIST:VOLT 0, 1, 2, 3 sets the LIST sequence to 0,1,2, and 3V on ch. 1.

    def _set_trigger_mode(self, stepped: bool) -> None:
        if stepped:
            return self._write_channel('sour:list:tmod {0},step')
            # Sets the trigger mode for the LIST sequence on channel {channel} to step.
            # step mode: Every time the LIST sequence receives a trigger signal it advances to the next value in the list.
        self._write_channel('sour:list:tmod {0},auto')
        # auto mode: (Default) Specifies that a trigger event should start the automatic run of the LIST sequence, advancing points automatically.

    def _set_direction(self, backwards: bool) -> None:
        if backwards:
            return self._write_channel('sour:list:dir {0},down')
            # LIST execution order goes from last element to first element.
        self._write_channel('sour:list:dir {0},up')
        # LIST execution order goes from first element to last element (default).

    def _set_repetitions(self) -> None:
        self._write_channel(f'sour:list:coun {"{0}"},{self._repetitions}')
        # sets the number of repetitions to {self._repetitions} for the list sequence

    def _perpetual(self) -> bool:
        return self._repetitions < 0

    def start(self) -> None:
        """Start the DC list generator
        """
        self._start('DC list')

    def append(self, voltages: Sequence[float]) -> None:
        """Append voltages to the existing list

        Arguments:
            voltages (Sequence[float]): Sequence of voltages
        """
        self._write_channel_floats('sour:list:volt:app {0},', voltages)
        self._make_ready_to_start()

    def points(self) -> int:
        """
        Returns:
            int: Number of steps in the DC list
        """
        return int(self._ask_channel('sour:list:poin? {0}'))

    def cycles_remaining(self) -> int:
        """
        Returns:
            int: Number of cycles remaining in the DC list
        """
        return int(self._ask_channel('sour:list:ncl? {0}'))

    def values_V(self) -> Sequence[float]:
        """
        Returns:
            Sequence[float]: List of voltages
        """
        return comma_sequence_to_list_of_floats(
            self._ask_channel('sour:list:volt? {0}'))


class SPDacChannel(InstrumentChannel):

    def __init__(self, parent: 'SPDac', name: str, channum: int):
        super().__init__(parent, name)
        self._channum = channum
        self.add_parameter(
            name='output_range',
            label='range',
            set_cmd='sour:rang {1},{0}'.format('{}', channum),
            get_cmd=f'sour:rang? {channum}',
            vals=validators.Enum('low', 'high')
        )
        self.add_parameter(
            name='output_state',
            label='output-state',
            set_cmd='sour:outp {1},{0}'.format('{}', channum),
            get_cmd=f'sour:outp? {channum}',
            get_parser=str,
            vals=validators.Enum('normal', 'clamped6k', 'tristate')
        )
        self.add_parameter(
            name='dc_constant_V',
            label=f'ch{channum}',
            unit='V',
            set_cmd=self._set_fixed_voltage_immediately,
            get_cmd=f'sour:volt? {channum}',
            get_parser=float,
            vals=validators.Numbers(-10.0, 10.0)
        )
        self.add_parameter(
            name='dc_last_V',
            label=f'ch{channum}',
            unit='V',
            get_cmd=f'sour:volt:last? {channum}',
            get_parser=float
        )
        # self.add_parameter(
        #     name='dc_next_V',
        #     label=f'ch{channum}',
        #     unit='V',
        #     set_cmd='sour:volt:trig {1},{0}'.format('{}', channum),
        #     get_cmd=f'sour:volt:trig? {channum}',
        #     get_parser=float
        # )
        self.add_parameter(
            name='dc_slew_rate_V_per_s',
            label=f'ch{channum}',
            unit='V/s',
            set_cmd='sour:volt:slew {1},{0}'.format('{}', channum),
            get_cmd=f'sour{channum}:volt:slew?',
            get_parser=float
        )
        self.add_parameter(
            name='dc_mode',
            label='DC mode',
            set_cmd='sour:volt:mode {1},{0}'.format('{}', channum),
            get_cmd=f'sour:volt:mode? {channum}',
            vals=validators.Enum('fixed', 'list', 'sweep')
        )
        self.add_parameter(
            name='ad_sample_V',
            label=f'ch{channum}',
            unit='V',
            get_cmd=f'meas:volt? {channum}',
            get_parser=float,
            vals=validators.Numbers(-10.0, 10.0)
        )
        self.add_function(
            name='dc_initiate',
            call_cmd=f'sour:dc:init {channum}'
        )
        self.add_function(
            name='dc_abort',
            call_cmd=f'sour:dc:abor {channum}'
        )
        self.add_function(
            name='abort',
            call_cmd=f'sour:all:abor {channum}'
        )

    @property
    def number(self) -> int:
        """Channel number"""
        return self._channum

    def output_mode(self, range: str = 'low', state: str = 'normal') -> None:
        """Set the output voltage

        Args:
            range (str, optional): low or high (default) voltage range
            state (str, optional): normal, clamped_6k or tristate (default) output state
        """
        self.output_range(range)
        self.output_state(state)

    def dc_list(self, voltages: Sequence[float], repetitions: int = 1,
                dwell_s: float = 1e-03, delay_s: float = 0,
                backwards: bool = False, stepped: bool = False
                ) -> List_Context:
        """Set up a DC-list generator

        Args:
            voltages (Sequence[float]): Voltages in list
            repetitions (int, optional): Number of repetitions of the list (default 1)
            dwell_s (float, optional): Seconds between each voltage (default 1ms)
            delay_s (float, optional): Seconds of delay after receiving a trigger (default 0)
            backwards (bool, optional): Use list in reverse (default is forward)
            stepped (bool, optional): True means that each step needs to be triggered (default False)

        Returns:
            List_Context: context manager
        """
        return List_Context(self, voltages, repetitions, dwell_s, delay_s,
                            backwards, stepped)

    def dc_sweep(self, start_V: float, stop_V: float, points: int,
                 repetitions: int = 1, dwell_s: float = 1e-03,
                 delay_s: float = 0, backwards=False, stepped=True
                 ) -> Sweep_Context:
        """Set up a DC sweep

        Args:
            start_V (float): Start voltage
            stop_V (float): Send voltage
            points (int): Number of steps
            repetitions (int, optional): Number of repetition (default 1)
            dwell_s (float, optional): Seconds between each voltage (default 1ms)
            delay_s (float, optional): Seconds of delay after receiving a trigger (default 0)
            backwards (bool, optional): Sweep in reverse (default is forward)
            stepped (bool, optional): True means discrete steps (default True)

        Returns:
            Sweep_Context: context manager
        """
        return Sweep_Context(self, start_V, stop_V, points, repetitions,
                             dwell_s, delay_s, backwards, stepped)

    def _set_fixed_voltage_immediately(self, v) -> None:
        self.write(f'sour:volt:mode {self._channum},fix')
        self.write(f'sour:volt {self._channum},{v}')

    def ask_channel(self, cmd: str) -> str:
        """Inject channel number into SCPI query

        Arguments:
            cmd (str): Must contain a '{0}' placeholder for the channel number

        Returns:
            str: SCPI answer
        """
        return self.ask(self._channel_message(cmd))

    def write_channel(self, cmd: str) -> None:
        """Inject channel number into SCPI command

        Arguments:
            cmd (str): Must contain a '{0}' placeholder for the channel number
        """
        self.write(self._channel_message(cmd))

    def write_channel_floats(self, cmd: str, values: Sequence[float]) -> None:
        """Inject channel number and a list of values into SCPI command

        The values are appended to the end of the command.

        Arguments:
            cmd (str): Must contain a '{0}' placeholder for channel number
            values (Sequence[float]): Sequence of numbers
        """
        self._parent.write_floats(self._channel_message(cmd), values)

    def write(self, cmd: str) -> None:
        """Send a SCPI command

        Args:
            cmd (str): SCPI command
        """
        self._parent.write(cmd)

    def _channel_message(self, template: str):
        return template.format(self._channum)


# this class contain some function with quatumn dot control
class Virtual_Sweep_Context:

    def __init__(self, arrangement: 'Arrangement_Context', sweep: np.ndarray,
                 start_trigger: Optional[str], step_time_s: float,
                 step_trigger: Optional[str], repetitions: Optional[int]):
        self._arrangement = arrangement
        self._sweep = sweep
        self._step_trigger = step_trigger
        self._step_time_s = step_time_s
        self._repetitions = repetitions
        self._allocate_triggers(start_trigger)
        self._spdac_ready = False

    def __enter__(self):
        self._ensure_spdac_setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Stop markers
        channel = self._get_channel(0)
        channel.write_channel(f'sour:dc:mark:sst {"{0}"} 0')
        # Stop any lists
        for contact_index in range(self._arrangement.shape):
            channel = self._get_channel(contact_index)
            channel.dc_abort()
            channel.write_channel(f'sour:dc:trig:sour {"{0}"} imm')
        # Let Arrangement take care of freeing triggers
        return False

    def close(self) -> None:
        self.__exit__(None, None, None)
        self._arrangement.close()

    def actual_values_V(self, contact: str) -> np.ndarray:
        """The corrected values that would actually be sent to the contact

        Args:
            contact (str): Name of contact

        Returns:
            np.ndarray: Corrected voltages
        """
        index = self._arrangement._contact_index(contact)
        return self._sweep[:, index]

    def start(self) -> None:
        """Start the 2D sweep
        """
        self._ensure_spdac_setup()
        trigger = self._arrangement.get_trigger_by_name(self._start_trigger_name)
        self._arrangement._spdac.trigger(trigger)

    def _allocate_triggers(self, start_sweep: Optional[str]) -> None:
        if not start_sweep:
            # Use a random, unique name
            start_sweep = uuid.uuid4().hex
        self._arrangement._allocate_internal_triggers([start_sweep])
        self._start_trigger_name = start_sweep

    def _ensure_spdac_setup(self) -> None:
        if self._spdac_ready:
            return self._make_ready_to_start()
        self._route_inner_trigger()
        self._send_lists_to_spdac()
        self._spdac_ready = True

    def _route_inner_trigger(self) -> None:
        if not self._step_trigger:
            return
        trigger = self._arrangement.get_trigger_by_name(self._step_trigger)
        # All channels change in sync, so just use the first channel to make the
        # external trigger.
        channel = self._get_channel(0)
        channel.write_channel(f'sour:dc:mark:sst {"{0}"} '
                              f'{_trigger_context_to_value(trigger)}')

    def _get_channel(self, contact_index: int) -> 'SPDacChannel':
        channel_number = self._arrangement._channels[contact_index]
        spdac = self._arrangement._spdac
        return spdac.channel(channel_number)

    def _send_lists_to_spdac(self) -> None:
        for contact_index in range(self._arrangement.shape):
            self._send_list_to_spdac(contact_index, self._sweep[:, contact_index])

    def _send_list_to_spdac(self, contact_index, voltages):
        channel = self._get_channel(contact_index)
        dc_list = channel.dc_list(voltages=voltages, dwell_s=self._step_time_s,
                                  repetitions=self._repetitions)
        trigger = self._arrangement.get_trigger_by_name(self._start_trigger_name)
        dc_list.start_on(trigger)

    def _make_ready_to_start(self):  # Bug circumvention
        for contact_index in range(self._arrangement.shape):
            channel = self._get_channel(contact_index)
            channel.write_channel('sour:dc:init {0}')


class Arrangement_Context:
    def __init__(self, spdac: 'SPDac', contacts: Dict[str, int],
                 output_triggers: Optional[Dict[str, int]],
                 internal_triggers: Optional[Sequence[str]],
                 outer_trigger_channel: Optional[int]):
        self._spdac = spdac
        self._fix_contact_order(contacts)
        self._allocate_triggers(internal_triggers, output_triggers)
        self._outer_trigger_channel = outer_trigger_channel
        self._correction = np.identity(self.shape)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._external_triggers:
            for port in self._external_triggers.values():
                self._spdac.write(f'outp:trig:sour {port},hold')
        self._free_triggers()
        return False

    def close(self) -> None:
        self.__exit__(None, None, None)

    @property
    def shape(self) -> int:
        """Number of contacts in the arrangement"""
        return len(self._contacts)

    @property
    def correction_matrix(self) -> np.ndarray:
        """Correction matrix"""
        return self._correction

    @property
    def contact_names(self) -> Sequence[str]:
        """
        Returns:
            Sequence[str]: Contact names in the same order as channel_numbers
        """
        return self._contact_names

    def _allocate_internal_triggers(self,
                                    internal_triggers: Optional[Sequence[str]]
                                    ) -> None:
        if not internal_triggers:
            return
        for name in internal_triggers:
            self._internal_triggers[name] = self._spdac.allocate_trigger()

    def initiate_correction(self, contact: str, factors: Sequence[float]) -> None:
        """Override how much a particular contact influences the other contacts

        Args:
            contact (str): Name of contact
            factors (Sequence[float]): factors between -1.0 and 1.0
        """
        index = self._contact_index(contact)
        self._correction[index] = factors

    def set_virtual_voltage(self, contact: str, voltage: float) -> None:
        """Set virtual voltage on specific contact

        The actual voltage that the contact will receive depends on the
        correction matrix.

        Args:
            contact (str): Name of contact
            voltage (float): Voltage corresponding to no correction
        """
        try:
            index = self._contact_index(contact)
        except KeyError:
            raise ValueError(f'No contact named "{contact}"')
        self._effectuate_virtual_voltage(index, voltage)

    def set_virtual_voltages(self, contacts_to_voltages: Dict[str, float]) -> None:
        """Set virtual voltages on specific contacts in one go

        The actual voltage that each contact will receive depends on the
        correction matrix.

        Args:
            contact_to_voltages (Dict[str,float]): contact to voltage map
        """
        for contact, voltage in contacts_to_voltages.items():
            try:
                index = self._contact_index(contact)
            except KeyError:
                raise ValueError(f'No contact named "{contact}"')
            self._virtual_voltages[index] = voltage
        self._effectuate_virtual_voltages()

    def _effectuate_virtual_voltage(self, index: int, voltage: float) -> None:
        self._virtual_voltages[index] = voltage
        self._effectuate_virtual_voltages()

    def _effectuate_virtual_voltages(self) -> None:
        for index, channel_number in enumerate(self._channels):
            actual_V = self.actual_voltages()[index]
            self._spdac.channel(channel_number).dc_constant_V(actual_V)

    def add_correction(self, contact: str, factors: Sequence[float]) -> None:
        """Update how much a particular contact influences the other contacts

        This is mostly useful in arrangements where each contact has significant
        effect only on nearby contacts, and thus can be added incrementally.

        The factors are extended by the identity matrix and multiplied to the
        correction matrix.

        Args:
            contact (str): Name of contact
            factors (Sequence[float]): factors usually between -1.0 and 1.0
        """
        index = self._contact_index(contact)
        multiplier = np.identity(self.shape)
        multiplier[index] = factors
        self._correction = np.matmul(multiplier, self._correction)

    def _fix_contact_order(self, contacts: Dict[str, int]) -> None:
        self._contact_names = list()
        self._contacts = dict()
        self._channels = list()
        index = 0
        for contact, channel in contacts.items():
            self._contact_names.append(contact)
            self._contacts[contact] = index
            index += 1
            self._channels.append(channel)
        self._virtual_voltages = np.zeros(self.shape)

    @property
    def channel_numbers(self) -> Sequence[int]:
        """
        Returns:
            Sequence[int]: Channels numbers in the same order as contact_names
        """
        return self._channels

    def channel(self, name: str) -> SPDacChannel:
        return self._spdac.channel(self._channels[self._contacts[name]])

    def virtual_voltage(self, contact: str) -> float:
        """
        Args:
            contact (str): Name of contact

        Returns:
            float: Voltage before correction
        """
        index = self._contact_index(contact)
        return self._virtual_voltages[index]

    def actual_voltages(self) -> Sequence[float]:
        """
        Returns:
            Sequence[float]: Corrected voltages for all contacts
        """
        vs = np.matmul(self._correction, self._virtual_voltages)
        if self._spdac._round_off:
            vs = np.round(vs, self._spdac._round_off)
        return list(vs)

    def get_trigger_by_name(self, name: str) -> SPDacTrigger_Context:
        """
        Args:
            name (str): Name of trigger

        Returns:
            SPDacTrigger_Context: Trigger context manager
        """
        try:
            return self._internal_triggers[name]
        except KeyError:
            print(f'Internal triggers: {list(self._internal_triggers.keys())}')
            raise

    def _all_channels_as_suffix(self) -> str:
        channels_str = ints_to_comma_separated_list(self.channel_numbers)
        return f'(@{channels_str})'

    def virtual_sweep(self, contact: str, voltages: Sequence[float],
                      start_sweep_trigger: Optional[str] = None,
                      step_time_s: float = 1e-5,
                      step_trigger: Optional[str] = None,
                      repetitions: int = 1) -> Virtual_Sweep_Context:
        """Sweep a contact to create a 1D sweep

        Args:
            contact (str): Name of sweeping contact
            voltages (Sequence[float]): Virtual sweep voltages
            outer_contact (str): Name of slow-changing (outer) contact
            start_sweep_trigger (None, optional): Trigger that starts sweep
            step_time_s (float, optional): Delay between voltage changes
            step_trigger (None, optional): Trigger that marks each step
            repetitions (int, Optional): Number of back-and-forth sweeps, or -1 for infinite

        Returns:
            Virtual_Sweep_Context: context manager
        """
        sweep = self._calculate_1d_values(contact, voltages)
        return Virtual_Sweep_Context(self, sweep, start_sweep_trigger,
                                     step_time_s, step_trigger, repetitions)

    def _calculate_1d_values(self, contact: str, voltages: Sequence[float]
                             ) -> np.ndarray:
        original_voltage = self.virtual_voltage(contact)
        index = self._contact_index(contact)
        sweep = list()
        for v in voltages:
            self._virtual_voltages[index] = v
            sweep.append(self.actual_voltages())
        self._virtual_voltages[index] = original_voltage
        return np.array(sweep)

    def _calculate_2d_values(self, inner_contact: str,
                             inner_voltages: Sequence[float],
                             outer_contact: str,
                             outer_voltages: Sequence[float]) -> np.ndarray:
        original_fast_voltage = self.virtual_voltage(inner_contact)
        original_slow_voltage = self.virtual_voltage(outer_contact)
        outer_index = self._contact_index(outer_contact)
        inner_index = self._contact_index(inner_contact)
        sweep = list()
        for slow_V in outer_voltages:
            self._virtual_voltages[outer_index] = slow_V
            for fast_V in inner_voltages:
                self._virtual_voltages[inner_index] = fast_V
                sweep.append(self.actual_voltages())
        self._virtual_voltages[inner_index] = original_fast_voltage
        self._virtual_voltages[outer_index] = original_slow_voltage
        return np.array(sweep)

    def virtual_detune(self, contacts: Sequence[str], start_V: Sequence[float],
                       end_V: Sequence[float], steps: int,
                       start_trigger: Optional[str] = None,
                       step_time_s: float = 1e-5,
                       step_trigger: Optional[str] = None,
                       repetitions: int = 1) -> Virtual_Sweep_Context:
        """Sweep any number of contacts linearly from one set of values to another set of values

        Args:
            contacts (Sequence[str]): contacts involved in sweep
            start_V (Sequence[float]): First-extreme values
            end_V (Sequence[float]): Second-extreme values
            steps (int): Number of steps between extremes
            start_trigger (None, optional): Trigger that starts sweep
            step_time_s (float, Optional): Seconds between each step
            step_trigger (None, optional): Trigger that marks each step
            repetitions (int, Optional): Number of back-and-forth sweeps, or -1 for infinite
        """
        self._check_same_lengths(contacts, start_V, end_V)
        sweep = self._calculate_detune_values(contacts, start_V, end_V, steps)
        return Virtual_Sweep_Context(self, sweep, start_trigger, step_time_s,
                                     step_trigger, repetitions)

    @staticmethod
    def _check_same_lengths(contacts, start_V, end_V) -> None:
        n_contacts = len(contacts)
        if n_contacts != len(start_V):
            raise ValueError(f'There must be exactly one voltage per contact: {start_V}')
        if n_contacts != len(end_V):
            raise ValueError(f'There must be exactly one voltage per contact: {end_V}')

    def _calculate_detune_values(self, contacts: Sequence[str], start_V: Sequence[float],
                                 end_V: Sequence[float], steps: int):
        original_voltages = [self.virtual_voltage(contact) for contact in contacts]
        indices = [self._contact_index(contact) for contact in contacts]
        sweep = list()
        forward_V = [forward_and_back(start_V[i], end_V[i], steps) for i in range(len(contacts))]
        for voltages in zip(*forward_V):
            for index, voltage in zip(indices, voltages):
                self._virtual_voltages[index] = voltage
            sweep.append(self.actual_voltages())
        for index, voltage in zip(indices, original_voltages):
            self._virtual_voltages[index] = voltage
        return np.array(sweep)

    def _contact_index(self, contact: str) -> int:
        return self._contacts[contact]

    def _allocate_triggers(self, internal_triggers: Optional[Sequence[str]],
                           output_triggers: Optional[Dict[str, int]]
                           ) -> None:
        self._internal_triggers: Dict[str, SPDacTrigger_Context] = dict()
        self._allocate_internal_triggers(internal_triggers)
        self._allocate_external_triggers(output_triggers)

    def _allocate_external_triggers(self, output_triggers:
                                    Optional[Dict[str, int]]
                                    ) -> None:
        self._external_triggers = dict()
        if not output_triggers:
            return
        for name, port in output_triggers.items():
            self._external_triggers[name] = port
            trigger = self._spdac.allocate_trigger()
            self._spdac.connect_external_trigger(port, trigger)
            self._internal_triggers[name] = trigger

    def _free_triggers(self) -> None:
        for trigger in self._internal_triggers.values():
            self._spdac.free_trigger(trigger)


def forward_and_back(start: float, end: float, steps: int):
    forward = np.linspace(start, end, steps)
    backward = np.flip(forward)[1:][:-1]
    back_and_forth = itertools.chain(forward, backward)
    return back_and_forth


class SPDac(VisaInstrument):

    def __init__(self, name: str, address: str, **kwargs) -> None:
        """Connect to a SPDAC

        Args:
            name (str): Name for instrument
            address (str): Visa identification string
            **kwargs: additional argument to the Visa driver
        """
        self._check_instrument_name(name)
        super().__init__(name, address, terminator='\n', **kwargs)
        self._set_up_serial()
        self._set_up_debug_settings()
        self._set_up_channels()
        self._set_up_external_triggers()
        self._set_up_internal_triggers()
        self._set_up_simple_functions()
        self.connect_message()
        self._check_for_wrong_model()
        self._check_for_incompatiable_firmware()
        self._set_up_manual_triggers()

    def n_channels(self) -> int:
        """
        Returns:
            int: Number of channels
        """
        return len(self.submodules['channels'])

    def channel(self, ch: int) -> SPDacChannel:
        """
        Args:
            ch (int): Channel number

        Returns:
            SPDacChannel: Visa representation of the channel
        """
        return getattr(self, f'ch{ch:02}')

    @staticmethod
    def n_triggers() -> int:
        """
        Returns:
            int: Number of internal triggers
        """
        return 14

    @staticmethod
    def n_external_inputs() -> int:
        """
        Returns:
            int: Number of external input triggers
        """
        return 4

    def n_external_outputs(self) -> int:
        """
        Returns:
            int: Number of external output triggers
        """
        return len(self.submodules['external_triggers'])

    def allocate_trigger(self) -> SPDacTrigger_Context:
        """Allocate an internal trigger

        Does not have any effect on the instrument, only the driver.

        Returns:
            SPDacTrigger_Context: Context manager

        Raises:
            ValueError: no free triggers
        """
        try:
            number = self._internal_triggers.pop()
        except KeyError:
            raise ValueError('no free internal triggers')
        return SPDacTrigger_Context(self, number)

    def free_trigger(self, trigger: SPDacTrigger_Context) -> None:
        """Free an internal trigger

        Does not have any effect on the instrument, only the driver.

        Args:
            trigger (SPDacTrigger_Context): trigger to free
        """
        internal = _trigger_context_to_value(trigger)
        self._internal_triggers.add(internal)

    def free_all_triggers(self) -> None:
        """Free all an internal triggers

        Does not have any effect on the instrument, only the driver.
        """
        self._set_up_internal_triggers()

    def connect_external_trigger(self, port: int, trigger: SPDacTrigger_Context,
                                 width_s: float = 1e-6
                                 ) -> None:
        """Route internal trigger to external trigger

        Args:
            port (int): External output trigger number
            trigger (SPDacTrigger_Context): Internal trigger
            width_s (float, optional): Output trigger width in seconds (default 1ms)
        """
        internal = _trigger_context_to_value(trigger)
        self.write(f'outp:trig:sour {port},int{internal}')
        self.write(f'outp:trig:widt {port},{width_s}')

    def reset(self) -> None:
        self.write('*rst')
        sleep_s(5)

    def errors(self) -> str:
        """Retrieve and clear all previous errors

        Returns:
            str: Comma separated list of errors or '0, "No error"'
        """
        return self.ask('syst:err:all?')

    def error(self) -> str:
        """Retrieve next error

        Returns:
            str: The next error or '0, "No error"'
        """
        return self.ask('syst:err?')

    def n_errors(self) -> int:
        """Peek at number of previous errors

        Returns:
            int: Number of errors
        """
        return int(self.ask('syst:err:coun?'))

    def start_all(self) -> None:
        """Trigger the global SCPI bus (``*TRG``)

        All generators, that have not been explicitly set to trigger on an
        internal or external trigger, will be started.
        """
        self.write('*trg')

    def remove_traces(self) -> None:
        """Delete all trace definitions from the instrument

        This means that all AWGs loose their data.
        """
        self.write('trac:rem:all')

    def traces(self) -> Sequence[str]:
        """List all defined traces

        Returns:
            Sequence[str]: trace names
        """
        return comma_sequence_to_list(self.ask('trac:cat?'))

    def mac(self) -> str:
        """
        Returns:
            str: Media Access Control (MAC) address of the instrument
        """
        mac = self.ask('syst:comm:lan:mac?')
        return f'{mac[1:3]}-{mac[3:5]}-{mac[5:7]}-{mac[7:9]}-{mac[9:11]}' \
               f'-{mac[11:13]}'

    def arrange(self, contacts: Dict[str, int],
                output_triggers: Optional[Dict[str, int]] = None,
                internal_triggers: Optional[Sequence[str]] = None,
                outer_trigger_channel: Optional[int] = None
                ) -> Arrangement_Context:
        """An arrangement of contacts and triggers for virtual gates

        Each contact corresponds to a particular output channel.  Each
        output_trigger corresponds to a particular external output trigger.
        Each internal_trigger will be allocated from the pool of internal
        triggers, and can later be used for synchronisation.  After
        initialisation of the arrangement, contacts and triggers can only be
        referred to by name.

        The voltages that will appear on each contact depends not only on the
        specified virtual voltage, but also on a correction matrix.  Initially,
        the contacts are assumed to not influence each other, which means that
        the correction matrix is the identity matrix, ie. the row for
        each contact has a value of [0, ..., 0, 1, 0, ..., 0].

        Args:
            contacts (Dict[str, int]): Name/channel pairs
            output_triggers (Sequence[Tuple[str,int]], optional): Name/number pairs of output triggers
            internal_triggers (Sequence[str], optional): List of names of internal triggers to allocate
            outer_trigger_channel (int, optional): Additional channel if outer trigger is needed

        Returns:
            Arrangement_Context: context manager
        """
        return Arrangement_Context(self, contacts, output_triggers,
                                   internal_triggers, outer_trigger_channel)

    # -----------------------------------------------------------------------
    # Instrument-wide functions
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # Debugging and testing

    def start_recording_scpi(self) -> None:
        """Record all SCPI commands sent to the instrument

        Any previous recordings are removed.  To inspect the SCPI commands sent
        to the instrument, call get_recorded_scpi_commands().
        """
        self._scpi_sent: List[str] = list()
        self._record_commands = True

    def get_recorded_scpi_commands(self) -> List[str]:
        """
        Returns:
            Sequence[str]: SCPI commands sent to the instrument
        """
        commands = self._scpi_sent
        self._scpi_sent = list()
        return commands

    def clear(self) -> None:
        """Reset the VISA message queue of the instrument
        """
        self.visa_handle.clear()

    def clear_read_queue(self) -> Sequence[str]:
        """Flush the VISA message queue of the instrument

        Takes at least _message_flush_timeout_ms to carry out.

        Returns:
            Sequence[str]: Messages lingering in queue
        """
        lingering = list()
        original_timeout = self.visa_handle.timeout
        self.visa_handle.timeout = self._message_flush_timeout_ms
        while True:
            try:
                message = self.visa_handle.read()
            except VisaIOError:
                break
            else:
                lingering.append(message)
        self.visa_handle.timeout = original_timeout
        return lingering

    # -----------------------------------------------------------------------
    # Override communication methods to make it possible to record the
    # communication with the instrument.

    def write(self, cmd: str) -> None:
        """Send SCPI command to instrument

        Args:
            cmd (str): SCPI command
        """
        if self._record_commands:
            self._scpi_sent.append(cmd)
        super().write(cmd)

    def ask(self, cmd: str) -> str:
        """Send SCPI query to instrument

        Args:
            cmd (str): SCPI query

        Returns:
            str: SCPI answer
        """
        if self._record_commands:
            self._scpi_sent.append(cmd)
        answer = super().ask(cmd)
        return answer

    def write_floats(self, cmd: str, values: Sequence[float]) -> None:
        """Append a list of values to a SCPI command

        By default, the values are IEEE binary encoded.

        Remember to include separating space in command if needed.
        """
        if self._no_binary_values:
            compiled = f'{cmd}{floats_to_comma_separated_list(values)}'
            if self._record_commands:
                self._scpi_sent.append(compiled)
            return super().write(compiled)
        if self._record_commands:
            self._scpi_sent.append(f'{cmd}{floats_to_comma_separated_list(values)}')
        self.visa_handle.write_binary_values(cmd, values)

    # -----------------------------------------------------------------------

    def _set_up_debug_settings(self) -> None:
        self._record_commands = False
        self._scpi_sent = list()
        self._message_flush_timeout_ms = 1
        self._round_off = None
        self._no_binary_values = False

    def _set_up_serial(self) -> None:
        # No harm in setting the speed even if the connection is not serial.
        self.visa_handle.baud_rate = 921600  # type: ignore

    def _check_for_wrong_model(self) -> None:
        model = self.IDN()['model']
        if model != 'SPDAC':
            raise ValueError(f'Unknown model {model}. Are you using the right'
                             ' driver for your instrument?')

    def _check_for_incompatiable_firmware(self) -> None:
        # Only compare the firmware, not the FPGA version
        firmware = split_version_string_into_components(self.IDN()['firmware'])[1]
        least_compatible_fw = '1.0'
        if parse(firmware) < parse(least_compatible_fw):
            raise ValueError(f'Incompatible firmware {firmware}. You need at '
                             f'least {least_compatible_fw}')

    def _set_up_channels(self) -> None:
        channels = ChannelList(self, 'Channels', SPDacChannel,
                               snapshotable=False)
## channel number
        for i in range(1, 4 + 1):
## channel number
            name = f'ch{i:02}'
            channel = SPDacChannel(self, name, i)
            self.add_submodule(name, channel)
            channels.append(channel)
        channels.lock()
        self.add_submodule('channels', channels)

    def _set_up_external_triggers(self) -> None:
        triggers = ChannelList(self, 'Channels', SPDacExternalTrigger,
                               snapshotable=False)
        for i in range(1, 5 + 1):
            name = f'ext{i}'
            trigger = SPDacExternalTrigger(self, name, i)
            self.add_submodule(name, trigger)
            triggers.append(trigger)
        triggers.lock()
        self.add_submodule('external_triggers', triggers)

    def _set_up_internal_triggers(self) -> None:
        # A set of the available internal triggers
        self._internal_triggers = set(range(1, self.n_triggers() + 1))

    def _set_up_manual_triggers(self) -> None:
        self.add_parameter(
            name='trigger',
            # Manually trigger event
            set_parser=_trigger_context_to_value,
            set_cmd='tint {}',
        )

    def _set_up_simple_functions(self) -> None:
        self.add_function('abort', call_cmd='abor')

    def _check_instrument_name(self, name: str) -> None:
        if name.isidentifier():
            return
        raise ValueError(
            f'Instrument name "{name}" is incompatible with SPDev parameter '
            'generation (no spaces, punctuation, prepended numbers, etc)')
