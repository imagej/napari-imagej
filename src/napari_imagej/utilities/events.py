"""
Helper functions for working with the SciJava event bus.
"""


def subscribe(ij, subscriber):
    # NB: We need to retain a reference to this object or GC will delete it.
    ij.object().addObject(subscriber)
    _event_bus(ij).subscribe(subscriber.getEventClass(), subscriber)


def unsubscribe(ij, subscriber):
    _event_bus(ij).unsubscribe(subscriber.getEventClass(), subscriber)


def subscribers(ij, event_class):
    return _event_bus(ij).getSubscribers(event_class)


def _event_bus(ij):
    # HACK: Tap into the EventBus to obtain SciJava Module debug info.
    # See https://github.com/scijava/scijava-common/issues/452
    event_bus_field = ij.event().getClass().getDeclaredField("eventBus")
    event_bus_field.setAccessible(True)
    return event_bus_field.get(ij.event())
