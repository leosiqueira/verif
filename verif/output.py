# -*- coding: ISO-8859-1 -*-
import datetime
import inspect
import os
import re
import sys
import matplotlib.dates as mpldates
import matplotlib.pyplot as mpl
import numpy as np
import scipy.stats
import verif.axis
import verif.metric
import verif.metric_type
import verif.util
reload(sys)
sys.setdefaultencoding('ISO-8859-1')

allowedMapTypes = ["simple", "sat", "topo", "ESRI_Imagery_World_2D",
         "ESRI_StreetMap_World_2D", "I3_Imagery_Prime_World",
         "NASA_CloudCover_World", "NatGeo_World_Map", "NGS_Topo_US_2D",
         "Ocean_Basemap", "USA_Topo_Maps", "World_Imagery",
         "World_Physical_Map", "World_Shaded_Relief", "World_Street_Map",
         "World_Terrain_Base", "World_Topo_Map"]


def get_all():
   """
   Returns a dictionary of all output classes where the key is the class
   name (string) and the value is the class object
   """
   temp = inspect.getmembers(sys.modules[__name__], inspect.isclass)
   return temp


def get_all_by_type(type):
   """
   Like get_all, except only return metrics that are of a cerrtain
   verif.metric_type
   """
   temp = [output for output in get_all() if output[1].type == type]
   return temp


def get(name):
   """ Returns an instance of an object with the given class name """
   outputs = get_all()
   o = None
   for output in outputs:
      if name == output[0].lower() and output[1].is_valid():
         o = output[1]()
   return o


class Output(object):
   """
   Abstract class representing a plot

   usage:
   output = verif.output.QQ()
   output.plot(data)

   Attributes:
   aggregator
   axis
   bin_type
   bottom
   clim
   cmap
   dpi
   filename          When set, output the figure to this filename. File extension is
                     auto-detected.
   grid              When True, show a grid on the plot
   labfs
   left
   legfs
   leg_loc           Where should the legend be placed?
   line_colors
   line_styles
   xlog
   ylog
   lw                Line width
   map_type
   ms                Marker size
   pad
   require_threshold_type (str) : What type of thresholds does this metric
      require? One of 'None', 'deterministic', 'threshold', 'quantile'.
   right
   show_margin
   show_perfect
   thresholds
   quantiles
   tick_font_size
   title
   top
   xlabel
   xlim
   xrot
   xticklabels
   xticks
   ylabel
   ylim
   yticklabels
   yticks

   type
   """
   description = None
   default_axis = verif.axis.Leadtime()
   default_bin_type = "above"
   require_threshold_type = None
   supports_threshold = True
   supports_acc = False
   # It does not make sense to implement supports_aggregator here, since the
   # it gets complicated when an output uses a metric that may or may not allow
   # an aggregator
   supports_x = True
   reference = None
   _long = None
   type = verif.metric_type.Diagram()

   def __init__(self):
      self.aggregator = verif.aggregator.Mean()
      self.axis = self.default_axis
      self.bin_type = self.default_bin_type
      self.bottom = None
      self.clim = None
      self.cmap = mpl.cm.jet
      self.colors = None
      self.default_colors = ['r', 'b', 'g', [1, 0.73, 0.2], 'k']
      self.default_lines = ['-', '-', '-', '--']
      self.default_markers = ['o', '', '.', '']
      self.dpi = 100
      self.figsize = [5, 8]
      self.filename = None
      self.grid = True
      self.labfs = 16
      self.left = None
      self.leg_loc = "best"
      self.legfs = 16
      self.line_colors = None
      self.line_styles = None
      self.lw = 2
      self.map_type = None
      self.ms = 8
      self.quantiles = None
      self.right = None
      self.show_margin = True
      self.show_perfect = False
      self.simple = False
      self.styles = None
      self.thresholds = None
      self.tick_font_size = 16
      self.tickfs = 16
      self.tight = False
      self.title = None
      self.titlefs = 16
      self.top = None
      self.xlabel = None
      self.xlim = None
      self.xlog = False
      self.xrot = None
      self.xticklabels = None
      self.xticks = None
      self.ylabel = None
      self.ylim = None
      self.ylog = False
      self.yrot = None
      self.yticklabels = None
      self.yticks = None
      self.aspect = None

   @classmethod
   def name(cls):
      name = cls.__name__
      return name

   # Is this a valid output that should be created be called?
   @classmethod
   def is_valid(cls):
      return cls.description is not None

   @classmethod
   def help(cls):
      s = ""
      if cls.description is not None:
         s = cls.description
      if cls._long is not None:
         s = s + "\n" + verif.util.green("Description: ") + cls._long
      if cls.reference is not None:
         s = s + "\n" + verif.util.green("Reference: ") + cls.reference
      return s

   def plot(self, data, fig):
      """ Call this to create a plot
      """
      #mpl.clf()
      self._plot_core(data, fig)
      #self._adjust_axes(data)
      #self._legend(data)
      #self._save_plot(data)

   def text(self, data):
      """ Call this to create nicely formatted text output

      Prints to screen, unless self.filename is defined, in which case it
      writes to file.
      """
      [x, y, xlabel, ylabels] = self._get_x_y(data, self.axis)

      lengths = [max(11, len(label)+1) for label in ylabels]

      # Get column descriptions
      if self.axis == verif.axis.Threshold():
         descs = {"Threshold": self.thresholds}
      else:
         descs = data.get_axis_descriptions(self.axis)
      s = ','.join(descs.keys()) + ',' + ','.join(ylabels) + '\n'

      desc_lengths = dict()
      for w in descs.keys():
         desc_lengths[w] = max(11, len(w)+1)

      # Header line
      s = ""
      for w in descs.keys():
         # Axis descriptiors
         s += "%-*s| " % (desc_lengths[w], w)
      for i in range(len(ylabels)):
         # Labels
         s += "%-*s| " % (lengths[i], ylabels[i])
      s += "\n"

      # Loop over rows
      for i in range(0, len(x)):
         for w in descs.keys():
            if isinstance(descs[w][i], basestring):
               s += "%-*s| " % (desc_lengths[w], descs[w][i])
            else:
               # Don't use .4g because this will give unnecessary descimals for
               # location ids
               s += "%-*g| " % (desc_lengths[w], descs[w][i])
         for f in range(0, y.shape[1]):
            s += "%-*.4g| " % (lengths[f], y[i, f])
         s += "\n"

      # Remove last newline
      s = s.strip()

      if self.filename is not None:
         file = open(self.filename, 'w')
         file.write(s)
         file.write("\n")
         file.close()
      else:
         print s

   def csv(self, data):
      """ Call this to create machine-readable csv output

      Prints to screen, unless self.filename is defined, in which case it
      writes to file.
      """
      x, y, _, labels = self._get_x_y(data, self.axis)

      # Get column descriptions
      if self.axis == verif.axis.Threshold():
         descs = {"Threshold": self.thresholds}
      else:
         descs = data.get_axis_descriptions(self.axis)
      s = ','.join(descs.keys()) + ',' + ','.join(labels) + '\n'

      # Loop over rows
      for i in range(0, len(x)):
         line = ""
         line += ','.join(str(descs[k][i]) for k in descs)
         for f in range(0, y.shape[1]):
            line = line + ',%g' % y[i, f]
         s += line + "\n"

      # Remove last newline
      s = s.strip()

      if self.filename is not None:
         file = open(self.filename, 'w')
         file.write(s)
         file.write("\n")
         file.close()
      else:
         print s

   def _get_x_y(self, data, axis):
      """ Retrieve x and y axis values

      Returns:
         x (np.array): X-axis values
         y (np.array): 2D array with Y-axis values, one column for each line
         xname:
         ynames:
      """
      verif.util.error("This output does not provide text output")

   # Draws a map of the data
   def map(self, data):
      mpl.clf()
      self._map_core(data)
      self._adjust_axes(data)
      self._save_plot(data)

   def _plot_perfect_score(self, x, y, label="ideal", color="gray", zorder=-1000, always_show=0):
      """ Plots a line representing the perfect score

      Arguments:
         x (np.array): x-axis values
         y (float or np.array): y-axis values. If a float, then assume the same
            y-axis values for all x-axis values
         label: Add this label to the legend
         color: Line color
         zorder: zorder of the line
         always_show: If True, force the line to be shown, otherwise only show
            if self.show_perfect is set to True
      """
      if y is None:
         return
      if self.show_perfect or always_show:
         # Make 'perfect' same length as 'x'
         if not hasattr(y, "__len__"):
            y = y * np.ones(len(x), 'float')
         mpl.plot(x, y, '-', lw=5, color=color, label=label, zorder=zorder)

   def _plot_perfect_diagonal(self, label="ideal", color="gray", zorder=-1000, always_show=0):
      """ Plots a diagonal line representing the perfect score """
      axismin = min(min(mpl.ylim()), min(mpl.xlim()))
      axismax = max(max(mpl.ylim()), max(mpl.xlim()))
      if self.xlim is not None:
         axismin = min(axismin, self.xlim[0])
         axismax = max(axismax, self.xlim[1])
      if self.ylim is not None:
         axismin = max(axismin, self.ylim[0])
         axismax = min(axismax, self.ylim[1])

      self._plot_perfect_score([axismin, axismax],  [axismin, axismax],
            label=label, color=color, zorder=zorder, always_show=always_show)

   # Implement these methods
   def _plot_core(self, data):
      verif.util.error("This type does not plot")

   def _map_core(self, data):
      verif.util.error("This type does not produce maps")

   # Helper functions
   def _get_color(self, i, total):
      """ Returns a color specification (e.g. 0.3,0.3,1) that can be used in
      mpl to specify line color. Determined by looping through a database
      (self.line_colors). Returns the color for the i'th line in a plot of
      'total' number of lines.

      _get_color together with _get_style can be used to specify unique
      color/style combinations for many lines. Color is cycled first, then
      style. I.e. the following order is default:
      r-o, b-o, g-o, ..., r-, b-, g-, ...

      Arguments:
         i (int): Which line is this?
         total (int): Total number of lines in plot
      """
      if self.line_colors is not None:
         firstList = self.line_colors.split(",")
         numList = []
         finalList = []

         for string in firstList:
            if "[" in string:   # for rgba args
               if not numList:
                  string = string.replace("[", "")
                  numList.append(float(string))
               else:
                  verif.util.error("Invalid rgba arg \"{}\"".format(string))

            elif "]" in string:
               if numList:
                  string = string.replace("]", "")
                  numList.append(float(string))
                  finalList.append(numList)
                  numList = []
               else:
                  verif.util.error("Invalid rgba arg \"{}\"".format(string))

            # append to rgba lists if present, otherwise grayscale intensity
            elif verif.util.is_number(string):
               if numList:
                  numList.append(float(string))
               else:
                  finalList.append(string)

            else:
               if not numList:  # string args and hexcodes
                  finalList.append(string)
               else:
                  verif.util.error("Cannot read color args.")
         self.colors = finalList
         return self.colors[i % len(self.colors)]

      # use default colours if no colour input given
      else:
         self.colors = self.default_colors
         return self.colors[i % len(self.default_colors)]

   def _get_style(self, i, total, connectingLine=True, lineOnly=False):
      """ Returns a string (e.g. -o) that can be used in mpl to specify line
      style. Determined by looping through a database (self.line_styles).
      Returns the style for the i'th line in a plot of 'total' number of lines.

      Arguments:
         i (int): Which line is this?
         total (int): Total number of lines in plot
         connectingLine: If True, add a connecting line (e.g. -o) between the
            markers.  Otherwise only a marker will be used (e.g. o)
         lineOnly: If True, don't include the marker (e.g. -)
      """
      if self.line_styles is not None:
         listStyles = self.line_styles.split(",")
         # loop through input linestyles (independent of colors)
         I = i % len(listStyles)
         return listStyles[I]

      else:  # default linestyles
         I = (i / len(self.colors)) % len(self.default_lines)
         line = self.default_lines[I]
         marker = self.default_markers[I]
         if lineOnly:
            return line
         if connectingLine:
            return line + marker
         return marker

   # Saves to file, set figure size
   def _save_plot(self, data):
      if self.figsize is not None:
         mpl.gcf().set_size_inches(int(self.figsize[0]),
                                   int(self.figsize[1]), forward=True)
      if not self.show_margin:
         verif.util.remove_margin()

      if self.filename is not None:
         mpl.savefig(self.filename, bbox_inches='tight', dpi=self.dpi)
      else:
         fig = mpl.gcf()
         fig.canvas.set_window_title(data.get_names()[0])
         mpl.show()

   def _legend(self, data, names=None):
      if self.legfs > 0:
         if names is None:
            mpl.legend(loc=self.leg_loc, prop={'size': self.legfs})
         else:
            mpl.legend(names, loc=self.leg_loc, prop={'size': self.legfs})

   def _set_y_axis_limits(self, metric):
      currYlim = mpl.ylim()
      ylim = [metric.min, metric.max]
      if ylim[0] is None:
         ylim[0] = currYlim[0]
      if ylim[1] is None:
         ylim[1] = currYlim[1]
      mpl.ylim(ylim)

   def _adjust_axis(self, ax):
      """
      Make axis adjustments to a single axis
      """
      # Axis labels and title
      if self.xlabel is not None:
         ax.set_xlabel(self.xlabel)
      ax.set_xlabel(ax.get_xlabel(), fontsize=self.labfs)
      if self.ylabel is not None:
         ax.set_ylabel(self.ylabel)
      ax.set_ylabel(ax.get_ylabel(), fontsize=self.labfs)
      if self.title is not None:
         ax.set_title(self.title)
      ax.set_title(ax.get_title(), fontsize=self.titlefs)

      if self.aspect is not None:
         ax.set_aspect(self.aspect)

      if self.xlim is not None:
         xlim = self.xlim
         # Convert date to datetime objects
         if self.axis.is_time_like:
            xlim = [verif.util.date_to_datenum(lim) for lim in xlim]
         ax.set_xlim(xlim)
      if self.ylim is not None:
         ax.set_ylim(self.ylim)
      if self.xlog:
         ax.set_xscale('log')
      if self.ylog:
         ax.set_yscale('log')
      if self.grid:
         ax.grid('on')

      # Tick font sizes
      for tick in ax.xaxis.get_major_ticks():
         tick.label.set_fontsize(self.tickfs)
      for tick in ax.yaxis.get_major_ticks():
         tick.label.set_fontsize(self.tickfs)

      # Tick lines
      for label in ax.get_xticklabels():
         if self.xrot is not None:
            label.set_rotation(self.xrot)
         if self.tick_font_size is not None:
            label.set_fontsize(self.tick_font_size)
      for label in ax.get_yticklabels():
         if self.xrot is not None:
            label.set_rotation(self.yrot)
         if self.tick_font_size is not None:
            label.set_fontsize(self.tick_font_size)

      # X-ticks values
      if self.xticks is not None:
         # Convert date to datetime objects
         xticks = self.xticks
         if self.axis.is_time_like:
            xticks = [verif.util.date_to_datenum(tick) for tick in xticks]
         ax.set_xticks(xticks)
      if self.xticklabels is not None:
         ax.set_xticklabels(self.xticklabels)

      # Y-ticks values
      if self.yticks is not None:
         # Don't need to convert dates like for xticks, since these are never dates
         ax.set_yticks(self.yticks)
      if self.yticklabels is not None:
         ax.set_yticklabels(self.yticklabels)

   def _adjust_axes(self, data):
      """
      Adjust the labels, ticks, etc for axes on the plot. By default, only
      gca() is adjusted. To adjust all subplots, then this function should be
      overridden by the class (see PiHist for an example).
      """
      self._adjust_axis(mpl.gca())

      # Margins
      mpl.gcf().subplots_adjust(bottom=self.bottom, top=self.top, left=self.left, right=self.right)

   def _plot_obs(self, x, y, isCont=True, zorder=0, label="Observed"):
      if isCont:
         mpl.plot(x, y, ".-", color="gray", lw=5, label=label, zorder=zorder)
      else:
         mpl.plot(x, y, "o", color="gray", ms=self.ms, label=label,
               zorder=zorder)

   def _draw_circle(self, radius, xcenter=0, ycenter=0, maxradius=np.inf,
         style="--", color="k", lw=1, label="", zorder=-100):
      """
      Draws a circle
      radius      Radius of circle
      xcentre     x-axis value of centre of circle
      ycentre     y-axis value of centre of circle
      maxradius   Don't let the circle go outside an envelope circle with this
                  radius (centered on the origin)
      label       Use this text in the legend
      """
      angles = np.linspace(-np.pi / 2, np.pi / 2, 360)
      x = np.sin(angles) * radius + xcenter
      y = np.cos(angles) * radius + ycenter

      # Only keep points within the circle
      I = np.where(x ** 2 + y ** 2 < maxradius ** 2)[0]
      if len(I) == 0:
         return
      x = x[I]
      y = y[I]
      mpl.plot(x, y, style, color=color, lw=lw, zorder=zorder, label=label)
      mpl.plot(x, -y, style, color=color, lw=lw, zorder=zorder)

   def _plot_confidence(self, x, y, variance, n, color):
      # variance = y*(1-y) # For bins

      # Remove missing points
      I = np.where(n != 0)[0]
      if len(I) == 0:
         return
      x = x[I]
      y = y[I]
      variance = variance[I]
      n = n[I]

      z = 1.96  # 95% confidence interval
      type = "wilson"
      style = "--"
      if type == "normal":
         mean = y
         lower = mean - z * np.sqrt(variance / n)
         upper = mean + z * np.sqrt(variance / n)
      elif type == "wilson":
         mean = 1 / (1 + 1.0 / n * z ** 2) * (y + 0.5 * z ** 2 / n)
         upper = mean + 1 / (1 + 1.0 / n * z ** 2) * z * np.sqrt(variance / n +
               0.25 * z ** 2 / n ** 2)
         lower = mean - 1 / (1 + 1.0 / n * z ** 2) * z * np.sqrt(variance / n +
               0.25 * z ** 2 / n ** 2)
      mpl.plot(x, upper, style, color=color, lw=self.lw, ms=self.ms,
            label="")
      mpl.plot(x, lower, style, color=color, lw=self.lw, ms=self.ms,
            label="")
      verif.util.fill(x, lower, upper, color, alpha=0.3)

   @classmethod
   def get_class_name(cls):
      name = cls.__name__
      return name


class Standard(Output):
   """
   A standard plot of a metric from verif.metric
   """
   leg_loc = "best"
   supports_acc = True

   def __init__(self, metric):
      """
      metric:     an metric object from verif.metric
      """
      Output.__init__(self)
      self._metric = metric
      if metric.default_axis is not None:
         self.axis = metric.default_axis
      if metric.default_bin_type is not None:
         self.bin_type = metric.default_bin_type
      self.show_rank = False
      self.show_acc = False
      self.leg_sort = False
      self.show_smoothing_line = False  # Draw a smoothed line through the points
      self.show_missing = False  # Show missing stations on map

      # Settings
      self._mapLowerPerc = 0    # Lower percentile (%) to show in colourmap
      self._mapUpperPerc = 100  # Upper percentile (%) to show in colourmap
      self._mapLabelLocations = False  # Show locationIds in map?
      self._minLatLonRange = 0.001  # What is the smallest map size allowed (in degrees)

   def _get_x_y(self, data, axis):
      thresholds = self.thresholds

      intervals = verif.util.get_intervals(self.bin_type, thresholds)
      x = [i.center for i in intervals]
      if not axis == verif.axis.Threshold():
         x = data.get_axis_values(axis)
      if axis.is_time_like:
         x = [verif.util.unixtime_to_datenum(xx) for xx in x]
         x = [datetime.datetime.fromordinal(int(q)) + datetime.timedelta(days=q%1) -
               datetime.timedelta(days = 366) for q in x]

      xname = axis.name()
      ynames = data.get_legend()
      F = data.num_inputs
      y = None
      for f in range(0, F):
         yy = np.zeros(len(x), 'float')
         if axis == verif.axis.Threshold():
            for i in range(0, len(intervals)):
               yy[i] = self._metric.compute(data, f, axis, intervals[i])
         else:
            # Average all thresholds
            for i in range(0, len(intervals)):
               yy = yy + self._metric.compute(data, f, axis, intervals[i])
            yy = yy / len(intervals)

         if sum(np.isnan(yy)) == len(yy):
            verif.util.warning("No valid scores for " + ynames[f])
         if y is None:
            y = np.zeros([len(yy), F], 'float')
         y[:, f] = yy
      if self.show_acc:
         y = np.nan_to_num(y)
         y = np.cumsum(y, axis=0)
      return x, y, xname, ynames

   def _legend(self, data, names=None):
      if self.legfs > 0 and self.axis != verif.axis.No():
         mpl.legend(loc=self.leg_loc, prop={'size': self.legfs})

   def _plot_core(self, data, fig):
      import bokeh.plotting
      #bokeh.plotting.output_file("test.html")

      # We have to derive the legend list here, because we might want to
      # specify the order
      labels = np.array(data.get_legend())

      F = data.num_inputs
      [x, y, _, labels] = self._get_x_y(data, self.axis)

      # Sort legend entries such that the appear in the same order as the
      # y-values of the lines
      if self.leg_sort:
         if not self.show_acc:
            # averaging for non-acc plots
            averages = (verif.util.nanmean(y, axis=1))
            ids = averages.argsort()[::-1]

         else:
            ends = y[:, -1]  # take last points for acc plots
            ids = ends.argsort()[::-1]

         labels = [labels[i] for i in ids]

      else:
         ids = range(0, F)

      # Show a bargraph with unconditional averages when no axis is specified
      if self.axis == verif.axis.No():
         w = 0.8
         x = np.linspace(1 - w / 2, F - w / 2, F)
         mpl.bar(x, y[0, :], color='w', lw=self.lw)
         mpl.xticks(range(1, F + 1), labels)
      else:
         for f in range(0, F):
            id = ids[f]
            # colors and styles to follow labels
            color = self._get_color(id, F)
            style = self._get_style(id, F, self.axis.is_continuous)
            alpha = (1 if self.axis.is_continuous else 0.55)
            print "Adding line %s" % color
            fig.line(x, y[:, id], legend=labels[f], line_color=color)
            #mpl.plot(x, y[:, id], style, color=color,
            #      label=labels[f], lw=self.lw, ms=self.ms,
            #      alpha=alpha)
            if self.show_smoothing_line:
               import scipy.ndimage
               I = np.argsort(x)
               xx = np.sort(x)
               yy = y[:, id][I]
               I = np.where((np.isnan(xx) == 0) & (np.isnan(yy) == 0))[0]
               xx = xx[I]
               yy = yy[I]
               N = 21
               yy = scipy.ndimage.convolve(yy, 1.0/N*np.ones(N), mode="mirror")
               mpl.plot(xx, yy, "--", color=color, lw=self.lw, ms=self.ms)

         #mpl.xlabel(self.axis.label(data.variable))
         fig.xaxis.axis_label = self.axis.label(data.variable)

         """
         if self.axis.is_time_like:
            # Note that if the above plotted lines all have nan y'values, then
            # xaxis_date() will cause an error, since the x-axis limits are set
            # such that the plot is around 0. Override the x-limits so that the
            # user at least does not get a cryptic error message.
            if np.sum(np.isnan(y) == 0) == 0:
               mpl.xlim([min(x), max(x)])
            mpl.gca().xaxis_date()
         else:
            # NOTE: Don't call the locator on a date axis
            mpl.gca().xaxis.set_major_locator(data.get_axis_locator(self.axis))
         """
      #bokeh.plotting.show(fig)

      #mpl.ylabel(self._metric.label(data.variable))
      fig.yaxis.axis_label = self._metric.label(data.variable)
      perfect_score = self._metric.perfect_score
      """
      self._plot_perfect_score(mpl.xlim(), perfect_score)

      if not self.show_acc:
         self._set_y_axis_limits(self._metric)

      if self.tight:
         oldTicks = mpl.gca().get_xticks()
         diff = oldTicks[1] - oldTicks[0]  # keep auto tick interval
         tickRange = np.arange(round(np.min(x)), round(np.max(x)) + diff, diff)
         # make new ticks, to start from the first day of the desired interval
         mpl.gca().set_xticks(tickRange)
         mpl.autoscale(enable=True, axis=u'x', tight=True)  # make xaxis tight
      """

   def _map_core(self, data):
      # Use the Basemap package if it is available
      hasBasemap = True
      try:
         import mpl_toolkits.basemap
      except ImportError:
         verif.util.warning("Cannot load Basemap package")
         hasBasemap = False

      labels = data.get_legend()
      F = data.num_inputs
      lats = np.array([loc.lat for loc in data.locations])
      lons = np.array([loc.lon for loc in data.locations])
      ids = np.array([loc.id for loc in data.locations])
      dlat = max(lats) - min(lats)
      dlon = max(lons) - min(lons)
      llcrnrlat = max(-90, min(lats) - dlat / 10)
      urcrnrlat = min(90, max(lats) + dlat / 10)
      llcrnrlon = min(lons) - dlon / 10
      urcrnrlon = max(lons) + dlon / 10
      if llcrnrlat > urcrnrlat - self._minLatLonRange:
         llcrnrlat = llcrnrlat - self._minLatLonRange/2.0
         urcrnrlat = urcrnrlat + self._minLatLonRange/2.0
      if llcrnrlon > urcrnrlon - self._minLatLonRange:
         llcrnrlon = llcrnrlon - self._minLatLonRange/2.0
         urcrnrlon = urcrnrlon + self._minLatLonRange/2.0

      # Check if we are wrapped across the dateline
      if max(lons) - min(lons) > 180:
         minEastLon = min(lons[lons > 0])
         maxWestLon = max(lons[lons < 0])
         if minEastLon - maxWestLon > 180:
            llcrnrlon = minEastLon - dlon / 10
            urcrnrlon = maxWestLon + dlon / 10 + 360
      if self.xlim is not None:
         llcrnrlon = self.xlim[0]
         urcrnrlon = self.xlim[1]
      if self.ylim is not None:
         llcrnrlat = self.ylim[0]
         urcrnrlat = self.ylim[1]

      res = verif.util.get_map_resolution(lats, lons)
      if dlon < 5:
         dx = 1
      elif dlon < 90:
         dx = 5
      else:
         dx = 10

      if dlat < 5:
         dy = 1
      elif dlat < 90:
         dy = 5
      else:
         dy = 10
      x, y, _, labels = self._get_x_y(data, verif.axis.Location())

      # Colorbar limits should be the same for all subplots
      clim = [verif.util.nanpercentile(y.flatten(), self._mapLowerPerc),
              verif.util.nanpercentile(y.flatten(), self._mapUpperPerc)]

      cmap = self.cmap

      # Forced limits
      if self.clim is not None:
         clim = self.clim

      std = verif.util.nanstd(y)
      minDiff = std / 50

      if F == 2 and self.show_rank:
         F = 1
      for f in range(0, F):
         verif.util.subplot(f, F)
         if self.map_type is not None and hasBasemap:
            map = mpl_toolkits.basemap.Basemap(llcrnrlon=llcrnrlon, llcrnrlat=llcrnrlat,
                  urcrnrlon=urcrnrlon, urcrnrlat=urcrnrlat, projection='cyl',
                  resolution=res, fix_aspect=False)
            map.drawcoastlines(linewidth=0.25)
            map.drawcountries(linewidth=0.25)
            map.drawmapboundary()
            map.drawparallels(np.arange(-90., 120., dy), labels=[1, 0, 0, 0])
            map.drawmeridians(np.arange(-180., 420., dx), labels=[0, 0, 0, 1])
            map.fillcontinents(color=[0.7, 0.7, 0.7], zorder=-1)
            x0, y0 = map(lons, lats)

            # Only show labels if specified
            if self.xlabel is not None:
               mpl.xlabel(self.xlabel, fontsize=self.labfs)
            if self.ylabel is not None:
               mpl.ylabel(self.ylabel, fontsize=self.labfs)

            # Draw background map
            if self.map_type != "simple":
               if self.map_type == "sat":
                  service = 'ESRI_Imagery_World_2D'
               elif self.map_type == "topo":
                  service = 'World_Topo_Map'
               else:
                  service = self.map_type
               Npixels = 1000
               map.arcgisimage(service=service, xpixels=Npixels, verbose=True)
         else:
            # Use matplotlibs plotting functions, if we do not use Basemap
            map = mpl
            x0 = lons
            y0 = lats
            mpl.xlim([llcrnrlon, urcrnrlon])
            mpl.ylim([llcrnrlat, urcrnrlat])

            # Default to show labels
            xlabel = ("Longitude" if self.xlabel is None else self.xlabel)
            ylabel = ("Latitude" if self.ylabel is None else self.ylabel)
            mpl.xlabel(xlabel, fontsize=self.labfs)
            mpl.ylabel(ylabel, fontsize=self.labfs)
         I = np.where(np.isnan(y[:, f]))[0]
         if self.show_missing:
            map.plot(x0[I], y0[I], 'kx')

         isMax = (y[:, f] == np.amax(y, 1)) &\
                 (y[:, f] > np.mean(y, 1) + minDiff)
         isMin = (y[:, f] == np.amin(y, 1)) &\
                 (y[:, f] < np.mean(y, 1) - minDiff)
         is_valid = (np.isnan(y[:, f]) == 0)
         s = self.ms*self.ms
         c0 = self._get_color(0, 2)
         c1 = self._get_color(1, 2)
         if self.show_rank:
            lmissing = None
            if self.show_missing and len(I) > 0:
               lmissing = map.scatter(x0[I], y0[I], s=s, c="k", marker="x")
            lsimilar = map.scatter(x0[is_valid], y0[is_valid], s=s, c="w")
            lmin = map.scatter(x0[isMin], y0[isMin], s=s, c=c1)
            lmax = map.scatter(x0[isMax], y0[isMax], s=s, c=c0)
         else:
            map.scatter(x0, y0, c=y[:, f], s=s, cmap=cmap)
            cb = map.colorbar()
            cb.set_label(self._metric.label(data.variable), fontsize=self.labfs)
            cb.set_clim(clim)
            mpl.clim(clim)
         if self._mapLabelLocations:
            for i in range(0, len(x0)):
               value = y[i, f]

               if not np.isnan(value):
                  mpl.text(x0[i], y0[i], "%d" % (ids[i]))
         names = data.get_legend()
         if self.title is not None:
            mpl.title(self.title)
         elif F > 1:
            mpl.title(names[f])
         elif F == 1 and self.show_rank:
            mpl.title(self._metric.name())
         self._adjust_axis(mpl.gca())

      # Legend
      if self.show_rank:
         if data.num_inputs > 2:
            lines = [lmin, lsimilar, lmax]
            names = ["min", "similar", "max"]
            if lmissing is not None:
                lines.append(lmissing)
                names.append("missing")
            mpl.figlegend(lines, names, "lower center", ncol=4)
         elif data.num_inputs == 2:
            lines = [lmax, lsimilar, lmin]
            names = [labels[0] + " is higher", "similar", labels[1] + " is higher"]
            if lmissing is not None:
                lines.append(lmissing)
                names.append("missing")
            mpl.legend(lines, names, loc=self.leg_loc, prop={'size': self.legfs})


class Hist(Output):
   require_threshold_type = "deterministic"
   supports_threshold = True
   supports_x = False
   default_bin_type = "within="

   def __init__(self, field):
      Output.__init__(self)
      self._field = field

      # Settings
      self._show_percent = True

   def _plot_core(self, data):
      F = data.num_inputs
      values = [data.get_scores(self._field, f, verif.axis.No()) for f in range(F)]

      labels = data.get_names()
      intervals = verif.util.get_intervals(self.bin_type, self.thresholds)
      x = [i.center for i in intervals]
      N = len(intervals)
      for f in range(0, F):
         y = np.zeros(N, float)
         # Compute how many are with each interval
         for i in range(0, N):
            y[i] = np.sum(intervals[i].within(values[f]))
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         if self._show_percent:
            y = y * 100.0 / np.sum(y)

         mpl.plot(x, y, style, color=color, label=labels[f], lw=self.lw, ms=self.ms)

      mpl.xlabel(verif.axis.Threshold().label(data.variable))
      if self._show_percent:
         mpl.ylabel("Frequency (%)")
      else:
         mpl.ylabel("Frequency")


class Sort(Output):
   supports_threshold = False
   supports_x = False

   def __init__(self, field):
      Output.__init__(self)
      self._field = field

   def _plot_core(self, data):
      F = data.num_inputs
      labels = data.get_legend()

      for f in range(0, F):
         x = np.sort(data.get_scores(self._field, f, verif.axis.No()))
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         y = np.linspace(0, 100, x.shape[0])
         mpl.plot(x, y, style, color=color, label=labels[f], lw=self.lw, ms=self.ms)
      mpl.xlabel("Sorted " + verif.axis.Threshold().label(data.variable))
      mpl.ylabel("Percentile (%)")


class ObsFcst(Output):
   supports_threshold = False
   description = "Plot observations and forecasts"

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      F = data.num_inputs
      isCont = self.axis.is_continuous

      x, y, _, labels = self._get_x_y(data, self.axis)

      # Show a bargraph with unconditional averages when no axis is specified
      if self.axis == verif.axis.No():
         w = 0.8
         x = np.linspace(1 - w / 2, len(labels) - w / 2, len(labels))
         mpl.bar(x, y[0, :], color='w', lw=self.lw)
         mpl.xticks(range(1, len(labels) + 1), labels)
      else:
         # Obs line
         self._plot_obs(x, y[:, 0], isCont)
         for f in range(0, F):
            color = self._get_color(f, F)
            style = self._get_style(f, F, isCont)
            mpl.plot(x, y[:, f + 1], style, color=color, label=labels[f+1], lw=self.lw, ms=self.ms)
         mpl.xlabel(self.axis.label(data.variable))
         if self.axis.is_time_like:
            mpl.gca().xaxis_date()
         else:
            mpl.gca().xaxis.set_major_formatter(self.axis.formatter(data.variable))

      mpl.ylabel(data.get_variable_and_units())

   def _get_x_y(self, data, axis):
      F = data.num_inputs
      x = data.get_axis_values(self.axis)
      if self.axis.is_time_like:
         x = [verif.util.unixtime_to_datenum(xx) for xx in x]

      # Obs line
      mObs = verif.metric.FromField(verif.field.Obs(), aux=verif.field.Fcst())
      mObs.aggregator = self.aggregator
      obs = mObs.compute(data, 0, self.axis, None)

      mFcst = verif.metric.FromField(verif.field.Fcst(), aux=verif.field.Obs())
      mFcst.aggregator = self.aggregator
      labels = data.get_legend()
      y = np.zeros([len(x), F + 1], float)
      y[:, 0] = obs
      for f in range(0, F):
         y[:, f + 1] = mFcst.compute(data, f, self.axis, None)

      labels = ["obs"] + labels
      return x, y, axis.name(), labels


class QQ(Output):
   supports_threshold = False
   supports_x = False
   description = "Quantile-quantile plot of obs vs forecasts"

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      labels = data.get_legend()
      F = data.num_inputs
      for f in range(0, F):
         [x, y] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f, verif.axis.No())
         x = np.sort(x)
         y = np.sort(y)
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         mpl.plot(x, y, style, color=color, label=labels[f], lw=self.lw, ms=self.ms)

      mpl.ylabel("Sorted forecasts (" + data.variable.units + ")")
      mpl.xlabel("Sorted observations (" + data.variable.units + ")")
      lims = verif.util.get_square_axis_limits(mpl.xlim(), mpl.ylim())
      mpl.xlim(lims)
      mpl.ylim(lims)
      self._plot_perfect_diagonal()
      mpl.gca().set_aspect(1)


class AutoCorr(Output):
   supports_threshold = False
   supports_x = True
   default_axis = verif.axis.Location()
   description = "Plots error auto-correlation as a function of distance. Use -x to specify axis to find auto-correlations for: -x location gives correlation between all pairs of locations; -x time gives between all pairs of forecast initializations; Similarly for -x leadtime, -x lat, -x lon, -x elev."

   def __init__(self):
      Output.__init__(self)

   @property
   def _show_smoothing_line(self):
      return not self.simple

   def _plot_core(self, data):
      labels = data.get_legend()
      F = data.num_inputs

      # Compute distances
      if self.axis.is_location_like:
         N = len(data.locations)
         dist = np.zeros([N, N])
         for i in range(N):
            for j in range(N):
               if self.axis == verif.axis.Location():
                  dist[i, j] = data.locations[i].get_distance(data.locations[j])/1000
               elif self.axis == verif.axis.Lat():
                  dist[i, j] = np.abs(data.locations[i].lat - data.locations[j].lat)
               elif self.axis == verif.axis.Lon():
                  dist[i, j] = np.abs(data.locations[i].lon - data.locations[j].lon)
               elif self.axis == verif.axis.Elev():
                  dist[i, j] = np.abs(data.locations[i].elev - data.locations[j].elev)
               else:
                  verif.util.error("Unknown location-like axis '%s'" % self.axis.name())
         if self.axis == verif.axis.Location():
            xlabel = "Distance (km)"
         elif self.axis == verif.axis.Lat():
            xlabel = "Latitude difference (degrees)"
         elif self.axis == verif.axis.Lon():
            xlabel = "Longitude difference (degrees)"
         elif self.axis == verif.axis.Elev():
            xlabel = "Elevation difference (m)"
      elif self.axis == verif.axis.Leadtime():
         N = len(data.leadtimes)
         dist = np.zeros([N, N])
         for i in range(N):
            for j in range(N):
               dist[i, j] = np.abs(data.leadtimes[i] - data.leadtimes[j])
         xlabel = "Leadtime difference (hours)"
      elif self.axis == verif.axis.Time():
         N = len(data.times)
         dist = np.zeros([N, N])
         for i in range(N):
            for j in range(N):
               dist[i, j] = np.abs(data.times[i] - data.times[j])/3600
         xlabel = "Time difference (hours)"
      else:
         verif.util.error("Axis '%s' not supported in AutCorr output" % self.axis.name())

      for f in range(0, F):
         corr = np.nan*np.zeros([N, N])
         [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f)
         error = obs - fcst
         min_dist = 0
         max_dist = 1e9
         if self.xlim is not None:
            min_dist = self.xlim[0]
            max_dist = self.xlim[1]
         for i in range(N):
            for j in range(N):
               if dist[i, j] >= min_dist and dist[i, j] <= max_dist:
                  if self.axis.is_location_like:
                     x = error[:, :, i].flatten()
                     y = error[:, :, j].flatten()
                  elif self.axis == verif.axis.Leadtime():
                     x = error[:, i, :].flatten()
                     y = error[:, j, :].flatten()
                  else:
                     x = error[i, :, :].flatten()
                     y = error[j, :, :].flatten()
                  I = np.where((np.isnan(x) == 0) & (np.isnan(y) == 0))[0]
                  corr[i, j] = np.corrcoef(x[I], y[I])[1, 0]
         color = self._get_color(f, F)
         style = self._get_style(f, F, False)
         x = dist.flatten()
         y = corr.flatten()
         mpl.plot(dist.flatten(), corr.flatten(), style, color=color, label=labels[f], lw=self.lw, ms=self.ms)
         if self._show_smoothing_line:
            if self.thresholds is None:
               percentiles = np.linspace(0, 100, 21)
               edges = np.array([np.percentile(np.unique(np.sort(x)), p) for p in percentiles])
            else:
               edges = self.thresholds
            quantiles = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]
            for q in range(len(quantiles)):
               quantile = quantiles[q]
               xx, yy = verif.util.bin(x, y, edges, lambda f: verif.util.nanpercentile(f, quantile*100))

               style = 'k-'
               lw = 2
               if q == 0 or q == len(quantiles)-1:
                  style = 'ko--'
               elif q == (len(quantiles)-1)/2:
                  style = 'ko-'
                  lw = 4
               # Write labels for the quantile lines, but only do it for one file
               label = ""
               if f == 0:
                  if q == 0 or q == len(quantiles) - 1:
                     label = "%d%%" % (quantiles[q] * 100)
                  # Instead of writing all labels, only summarize the middle ones
                  elif q == 1 and len(quantiles) > 3:
                     label = "%d%%-%d%%" % (quantiles[1] * 100, (quantiles[len(quantiles) - 2] * 100))
                  elif q == 1 and len(quantiles) == 3:
                     label = "%d%%" % (quantiles[1] * 100)
               mpl.plot(xx, yy, style, lw=lw, ms=self.ms,
                     zorder=100, label=label)
            self._plot_obs(x, 0*x, label="")

      mpl.xlabel(xlabel)
      mpl.ylabel("Error correlation")


class Scatter(Output):
   description = "Scatter plot of forecasts vs obs and lines showing quantiles of obs given forecast (use -r to specify)"
   supports_threshold = False
   supports_x = False

   def __init__(self):
      Output.__init__(self)
      self._max_points = 1e6

   def _show_quantiles(self):
      return not self.simple

   def _plot_core(self, data):
      labels = data.get_legend()
      F = data.num_inputs
      for f in range(0, F):
         [x, y] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f, verif.axis.No())

         color = self._get_color(f, F)
         style = self._get_style(f, F, connectingLine=False)
         alpha = 0.2 if self.simple else 1
         mpl.plot(x, y, ".", color=color, label=labels[f], lw=self.lw, ms=self.ms, alpha=alpha)
         if self._show_quantiles():
            # Determine bin edges for computing quantiles
            # Use those provided by -r
            if self.thresholds is not None:
               edges = self.thresholds
            # For precip, we want a bin at exacly 0
            elif re.compile("Precip.*").match(data.variable.name):
               # Number of bins
               N = 10
               # The second to last edge should be such that we have at least
               # Nmin data points above
               Nmin = 50.0
               # But no lower than 90th percentile, incase we don't have very many values
               pUpper = max(90, 100.0 - Nmin / y.shape[0] * 100.0)
               edges = np.append(np.array([0]), np.linspace(0.001, np.percentile(y, pUpper), N - 1))
               edges = np.append(edges, np.array([np.max(y)]))
            # Regular variables
            else:
               # How many quantile boxes should we make?
               N = max(8, min(30, x.shape[0] / 100))

               # We want the lower bin to cointain at least 50 points, so find
               # which percentile will give us 50 points
               Nmin = 50.0
               # If we don't have very much data, then use an upper bound of 10%tile
               pLower = min(10, Nmin / y.shape[0] * 100.0)
               pUpper = 100.0 - pLower
               # Create evenly spaced values from the point where we have at 50
               # below to 50 above
               edges = np.linspace(np.percentile(y, pLower), np.percentile(y, pUpper), N)
               # Add on the end points
               edges = np.append(np.array([np.min(y)]), edges)
               edges = np.append(edges, np.array([np.max(y)]))

            bins = (edges[1:] + edges[0:-1])/2

            # What quantile lines should be drawn?
            quantiles = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99]
            values = np.nan*np.zeros([len(quantiles), len(bins)], 'float')
            for q in range(0, len(quantiles)):
               for i in range(0, len(bins)):
                  I = np.where((y >= edges[i]) & (y < edges[i+1]))[0]
                  if len(I) > 0:
                     values[q, i] = np.percentile(x[I], quantiles[q]*100)
               style = 'k-'
               lw = 2
               if q == 0 or q == len(quantiles)-1:
                  style = 'ko--'
               elif q == (len(quantiles)-1)/2:
                  style = 'ko-'
                  lw = 4
               # Write labels for the quantile lines, but only do it for one file
               label = ""
               if f == 0:
                  if q == 0 or q == len(quantiles) - 1:
                     label = "%d%%" % (quantiles[q] * 100)
                  # Instead of writing all labels, only summarize the middle ones
                  elif q == 1 and len(quantiles) > 3:
                     label = "%d%%-%d%%" % (quantiles[1] * 100, (quantiles[len(quantiles) - 2] * 100))
                  elif q == 1 and len(quantiles) == 3:
                     label = "%d%%" % (quantiles[1] * 100)
               mpl.plot(values[q, :], bins, style, lw=lw, alpha=0.5, label=label)
            for i in range(0, len(bins)):
               mpl.plot([values[1, i], values[-2, i]], [bins[i], bins[i]], 'k-')
      mpl.ylabel("Forecasts (" + data.variable.units + ")")
      mpl.xlabel("Observations (" + data.variable.units + ")")
      lims = verif.util.get_square_axis_limits(mpl.xlim(), mpl.ylim())
      mpl.xlim(lims)
      mpl.ylim(lims)
      self._plot_perfect_diagonal()
      mpl.gca().set_aspect(1)


class Change(Output):
   supports_threshold = False
   supports_x = False
   description = "Forecast skill (MAE) as a function of change in obs from previous forecast run"

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      labels = data.get_legend()
      # Find range
      [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], 0)
      change = obs[1:, Ellipsis] - obs[0:-1, Ellipsis]
      maxChange = np.nanmax(abs(change.flatten()))
      edges = np.linspace(-maxChange, maxChange, 20)
      bins = (edges[1:] + edges[0:-1]) / 2
      F = data.num_inputs

      for f in range(0, F):
         [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f)
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         change = obs[1:, Ellipsis] - obs[0:-1, Ellipsis]
         err = abs(obs - fcst)
         err = err[1:, Ellipsis]
         x = np.nan * np.zeros(len(bins), 'float')
         y = np.nan * np.zeros(len(bins), 'float')

         for i in range(0, len(bins)):
            I = (change > edges[i]) & (change <= edges[i + 1])
            y[i] = verif.util.nanmean(err[I])
            x[i] = verif.util.nanmean(change[I])
         mpl.plot(x, y, style, color=color, lw=self.lw, ms=self.ms, label=labels[f])
      self._plot_perfect_score(x, 0)
      mpl.xlabel("Daily obs change (" + data.variable.units + ")")
      mpl.ylabel("MAE (" + data.variable.units + ")")


class Cond(Output):
   description = "Plots forecasts as a function of obs (use -r to specify bin-edges)"
   default_axis = verif.axis.Threshold()
   default_bin_type = "within="
   require_threshold_type = "deterministic"
   supports_threshold = True
   supports_x = False

   def supports_threshold(self):
      return True

   def _plot_core(self, data):
      intervals = verif.util.get_intervals(self.bin_type, self.thresholds)

      labels = data.get_legend()
      F = data.num_inputs
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)

         of = np.zeros(len(intervals), 'float')
         fo = np.zeros(len(intervals), 'float')
         xof = np.zeros(len(intervals), 'float')
         xfo = np.zeros(len(intervals), 'float')
         mof = verif.metric.Conditional(verif.field.Obs(), verif.field.Fcst(), np.mean)  # F | O
         mfo = verif.metric.Conditional(verif.field.Fcst(), verif.field.Obs(), np.mean)  # O | F
         xmof = verif.metric.XConditional(verif.field.Obs(), verif.field.Fcst())  # F | O
         xmfo = verif.metric.XConditional(verif.field.Fcst(), verif.field.Obs())  # O | F
         mof0 = verif.metric.Conditional(verif.field.Obs(), verif.field.Fcst(), np.mean)  # F | O
         for i in range(0, len(intervals)):
            fo[i] = mfo.compute(data, f, verif.axis.No(), intervals[i])
            of[i] = mof.compute(data, f, verif.axis.No(), intervals[i])
            xfo[i] = xmfo.compute(data, f, verif.axis.No(), intervals[i])
            xof[i] = xmof.compute(data, f, verif.axis.No(), intervals[i])
         mpl.plot(xof, of, style, color=color, label=labels[f] + " (F|O)",
               lw=self.lw, ms=self.ms)
         mpl.plot(fo, xfo, style, color=color, label=labels[f] + " (O|F)",
               lw=self.lw, ms=self.ms, alpha=0.5)
      mpl.ylabel("Forecasts (" + data.variable.units + ")")
      mpl.xlabel("Observations (" + data.variable.units + ")")
      lims = verif.util.get_square_axis_limits(mpl.xlim(), mpl.ylim())
      mpl.xlim(lims)
      mpl.ylim(lims)
      self._plot_perfect_diagonal()
      mpl.gca().set_aspect(1)


class SpreadSkill(Output):
   supports_threshold = True
   supports_x = False
   require_threshold_type = "deterministic"
   description = "Spread/skill plot showing RMSE of ensemble mean as a function of ensemble spread (use -r to specify spread thresholds and -q to specify a lower and upper quantile to represent spread)"

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      labels = data.get_legend()
      F = data.num_inputs
      if self.quantiles is not None:
         lower_q = np.min(self.quantiles)
         upper_q = np.max(self.quantiles)
      else:
         if len(data.quantiles) < 2:
            verif.util.error("Spread-skill diagram needs input files to have at least 2 quantiles")
         lower_q = data.quantiles[0]
         upper_q = data.quantiles[-1]
      lower_field = verif.field.Quantile(lower_q)
      upper_field = verif.field.Quantile(upper_q)
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F, connectingLine=False)
         [obs, fcst, lower, upper] = data.get_scores([verif.field.Obs(), verif.field.Fcst(), lower_field, upper_field], f, verif.axis.No())
         spread = upper - lower
         skill = (obs - fcst)**2
         x = np.nan*np.zeros(len(self.thresholds), 'float')
         y = np.nan*np.zeros(len(x), 'float')
         lower = np.nan*np.zeros(len(x), 'float')
         upper = np.nan*np.zeros(len(x), 'float')
         for i in range(1, len(self.thresholds)):
            I = np.where((np.isnan(spread) == 0) &
                         (np.isnan(skill) == 0) &
                         (spread > self.thresholds[i - 1]) &
                         (spread <= self.thresholds[i]))[0]
            if len(I) > 0:
               x[i] = np.mean(spread[I])
               y[i] = np.sqrt(np.mean(skill[I]))
               lower[i] = np.percentile(np.sqrt(skill[I]), 5)
               upper[i] = np.percentile(np.sqrt(skill[I]), 95)

         style = self._get_style(f, F)
         mpl.plot(x, y, style, color=color, lw=self.lw, ms=self.ms, label=labels[f])

      xlim = mpl.xlim(left=0)
      ylim = mpl.ylim(bottom=0)
      lims = np.array(verif.util.get_square_axis_limits(xlim, ylim))

      mpl.xlim(lims)
      mpl.ylim(lims)

      # The perfect score depends on how far the quantiles are apart. Compute
      # the number of standard deviations that the quantile interval would
      # contain assuming a Gaussian distribution. The ideal line will then be
      # scaled by this number.
      num_std = scipy.stats.norm.ppf(upper_q) - scipy.stats.norm.ppf(lower_q)
      self._plot_perfect_score(lims, 1.0/num_std*lims)

      mpl.xlabel("Width of the %g%% - %g%% interval (%s)" % (upper_q*100, lower_q*100, data.variable.units))
      mpl.ylabel("RMSE (" + data.variable.units + ")")


class TimeSeries(Output):
   description = "Plot observations and forecasts as a time series "\
         "(i.e. by concatinating all leadtimes). '-x <dimension>' has no "\
         "effect, as it is always shown by date."
   supports_threshold = False
   supports_x = False
   default_axis = verif.axis.Time()

   def _plot_core(self, data):
      F = data.num_inputs

      # Connect the last leadtime of a day with the first leadtime on the next day
      # This only makes sense if the obs/fcst don't span more than a day
      connect = min(data.leadtimes) + 24 > max(data.leadtimes)
      minLeadtime = min(data.leadtimes)

      times = data.times
      dates = [verif.util.unixtime_to_datenum(time) for time in times]
      # Draw observation line
      if verif.field.Obs() in data.get_fields():
         obs = data.get_scores(verif.field.Obs(), 0)
         for d in range(0, obs.shape[0]):
            x = dates[d] + data.leadtimes / 24.0
            y = verif.util.nanmean(obs[d, :, :], axis=1)
            if connect and d < obs.shape[0] - 1:
               obsmean = verif.util.nanmean(obs[d + 1, 0, :], axis=0)
               x = np.insert(x, x.shape[0], dates[d + 1] + minLeadtime / 24.0)
               y = np.insert(y, y.shape[0], obsmean)

            if d == 0:
               xmin = np.min(x)
            elif d == obs.shape[0] - 1:
               xmax = np.max(x)

            lab = "obs" if d == 0 else ""
            mpl.rcParams['ytick.major.pad'] = '20'
            mpl.rcParams['xtick.major.pad'] = '20'
            mpl.plot(x, y, ".-", color=[0.3, 0.3, 0.3], lw=5, label=lab)

      # Draw forecast lines
      if verif.field.Fcst() in data.get_fields():
         labels = data.get_legend()
         for f in range(0, F):
            fcst = data.get_scores(verif.field.Fcst(), f)
            color = self._get_color(f, F)
            style = self._get_style(f, F)
            for d in range(0, len(times)):
               x = dates[d] + data.leadtimes / 24.0
               y = verif.util.nanmean(fcst[d, :, :], axis=1)
               if connect and d < fcst.shape[0] - 1:
                  x = np.insert(x, x.shape[0], dates[d + 1] + minLeadtime / 24.0)
                  y = np.insert(y, y.shape[0], verif.util.nanmean(fcst[d + 1, 0, :]))
               lab = labels[f] if d == 0 else ""
               mpl.rcParams['ytick.major.pad'] = '20'
               mpl.rcParams['xtick.major.pad'] = '20'
               mpl.plot(x, y, style, color=color, lw=self.lw, ms=self.ms, label=lab)

      mpl.xlabel(self.axis.label(data.variable))
      if self.ylabel is None:
         mpl.ylabel(data.get_variable_and_units())
      else:
         mpl.ylabel(self.ylabel)
      mpl.gca().xaxis_date()

      if self.tight:
         oldTicks = mpl.gca().get_xticks()
         diff = oldTicks[1] - oldTicks[0]  # keep auto tick interval
         tickRange = np.arange(round(xmin), round(xmax) + diff, diff)
         # make new ticks, to start from the first day of the desired interval
         mpl.gca().set_xticks(tickRange)
         mpl.autoscale(enable=True, axis=u'x', tight=True)  # make xaxis tight


class Meteo(Output):
   description = "Plot a meteogram, with deterministic forecast, all quantile lines available (use -q to select a subset of quantiles), and observations. This makes most sense to use for a single location and forecast initialization time. If multiple dates and locations are used, then the average is used."
   supports_threshold = False
   supports_x = False
   _obs_col = [1, 0, 0]
   _fcst_col = [0, 1, 0]

   def _plot_core(self, data):
      F = data.num_inputs
      if F != 1:
         verif.util.error("Cannot use Meteo plot with more than 1 input file")
      x = [verif.util.unixtime_to_datenum(data.times[0] + lt*3600) for lt in data.leadtimes]
      isSingleTime = len(data.times) == 1

      # Plot obs line
      obs = data.get_scores(verif.field.Obs(), 0)
      obs = verif.util.nanmean(verif.util.nanmean(obs, axis=0), axis=1)
      mpl.plot(x, obs, "o-", color=self._obs_col, lw=2, ms=8, label="Observed")

      # Plot deterministic forecast
      fcst = data.get_scores(verif.field.Fcst(), 0)
      fcst = verif.util.nanmean(verif.util.nanmean(fcst, axis=0), axis=1)
      mpl.plot(x, fcst, "o-", color=self._fcst_col, lw=2, ms=8, label="Forecast")

      # Plot quantiles
      if self.quantiles is None:
         quantiles = np.sort(data.quantiles)
      else:
         quantiles = np.sort(self.quantiles)
      y = np.zeros([len(data.leadtimes), len(quantiles)], 'float')
      for i in range(0, len(quantiles)):
         score = data.get_scores(verif.field.Quantile(quantiles[i]), 0)
         y[:, i] = verif.util.nanmean(verif.util.nanmean(score, axis=0), axis=1)
      for i in range(0, len(quantiles)):
         style = "k-"
         if i == 0 or i == len(quantiles) - 1:
            style = "k--"
         label = "%d%%" % (quantiles[i]*100)
         mpl.plot(x, y[:, i], style, label=label, zorder=-1)

      # Fill areas betweeen lines
      Ncol = (len(quantiles)-1)/2
      for i in range(0, Ncol):
         color = [(1 - (i + 0.0) / Ncol)] * 3
         verif.util.fill(x, y[:, i], y[:, len(quantiles) - 1 - i], color,
               zorder=-2)

      # Labels and ticks
      if self.ylabel is None:
         mpl.ylabel(data.get_variable_and_units())
      else:
         mpl.ylabel(self.ylabel)
      mpl.gca().xaxis_date()

      if self.xlim is not None:
         mpl.xlim([verif.util.date_to_datenum(lim) for lim in self.xlim])
      else:
         if np.min(x) == np.max(x):
            mpl.xlim(x[0], x[0] + 1)
         else:
            mpl.xlim(np.min(x), np.max(x))
      mpl.gca().xaxis.set_major_locator(mpldates.DayLocator(interval=1))
      mpl.gca().xaxis.set_minor_locator(mpldates.HourLocator(interval=6))
      mpl.gca().xaxis.set_major_formatter(mpldates.DateFormatter('\n  %a %d %b %Y'))
      mpl.gca().xaxis.set_minor_formatter(mpldates.DateFormatter('%H'))

      # Hour labels
      minlabels = [tick.label1 for tick in mpl.gca().xaxis.get_minor_ticks()]
      for i in minlabels:
         i.set_fontsize(self.tickfs)

      # Date labels
      majlabels = [tick.label1 for tick in mpl.gca().xaxis.get_major_ticks()]
      for i in range(0, len(majlabels)):
         label = majlabels[i]
         if isSingleTime and i < len(majlabels)-1:
            label.set_horizontalalignment('left')
            label.set_verticalalignment('top')
            label.set_fontsize(self.tickfs)
            # Moves major labels to the top of the graph. The x-coordinate
            # seems to be irrelevant. When y-coord is 1, the label is near the
            # top. For 1.1 it is above the graph
            label.set_position((0, -0.035))
         else:
            # Turn off the last date label, since it is outside the graph
            label.set_visible(0)
      if not isSingleTime:
         mpl.xlabel("Time of day (h)")

      mpl.gca().xaxis.grid(True, which='major', color='k', zorder=-10, linestyle='-', linewidth=2)
      mpl.gca().xaxis.grid(True, which='minor', color='k', zorder=0, linestyle='--')
      mpl.gca().yaxis.grid(True, which='major', color='k', zorder=0)


class PitHist(Output):
   description = "Histogram of PIT values. Use -r to specify bins."
   supports_threshold = False
   supports_x = False

   def __init__(self):
      Output.__init__(self)
      self._num_bins = 10
      self._bar_color = "gray"

   def _show_stats(self):
      return False

   def _show_expected_line(self):
      return not self.simple

   def _legend(self, data, names=None):
      pass

   def _plot_core(self, data):
      F = data.num_inputs
      if self.thresholds is None:
         edges = np.linspace(0, 1, self._num_bins + 1)
      else:
         edges = self.thresholds
      num_bins = len(edges)-1
      labels = data.get_legend()
      for f in range(0, F):
         verif.util.subplot(f, F)
         [pit] = data.get_scores([verif.field.Pit()], f, verif.axis.No())

         N = np.histogram(pit, edges)[0]
         y = N * 1.0 / sum(N) * 100
         width = 1.0 / (len(edges)-1)
         mpl.bar(edges[0:-1], y, width=width, color=self._bar_color)

         # Plot expected mean line
         mpl.plot([0, 1], [100.0 / num_bins, 100.0 / num_bins], 'k--')

         # Axes and labels
         mpl.title(labels[f])
         ytop = 200.0 / num_bins
         mpl.ylim([0, ytop])
         mpl.xlim([0, 1])
         if f == 0:
            mpl.ylabel("Frequency (%)")

         # Draw red confidence band
         if self._show_expected_line():
            # Multiply by 100 to get to percent
            std = verif.metric.PitDev.deviation_std(pit, num_bins) * 100

            mpl.plot([0, 1], [100.0 / num_bins - 2 * std, 100.0 / num_bins - 2 * std], "r-")
            mpl.plot([0, 1], [100.0 / num_bins + 2 * std, 100.0 / num_bins + 2 * std], "r-")
            lower = [100.0 / num_bins - 2 * std, 100.0 / num_bins - 2 * std]
            upper = [100.0 / num_bins + 2 * std, 100.0 / num_bins + 2 * std]
            verif.util.fill([0, 1], lower, upper, "r", zorder=100, alpha=0.5)

         # Compute calibration deviation
         if self._show_stats():
            D = verif.metric.PitDev.deviation(pit, num_bins)
            D0 = verif.metric.PitDev.expected_deviation(pit, num_bins)
            ign = verif.metric.PitDev.ignorance_potential(pit, num_bins)
            mpl.text(0, mpl.ylim()[1], "Dev: %2.4f\nExp: %2.4f\nIgn: %2.4f"
                  % (D, D0, ign), verticalalignment="top")

         mpl.xlabel("Cumulative probability")

   def _adjust_axes(self, data):
      # Apply adjustements to all subplots
      for ax in mpl.gcf().get_axes():
         self._adjust_axis(ax)

      # Margins
      mpl.gcf().subplots_adjust(bottom=self.bottom, top=self.top, left=self.left, right=self.right)


class Discrimination(Output):
   description = "Discrimination diagram for a certain threshold (-r)"
   supports_x = False

   def __init__(self):
      Output.__init__(self)
      self._num_bins = 10

   def _plot_core(self, data):
      if self.thresholds is None or len(self.thresholds) != 1:
         verif.util.error("Discrimination diagram requires exactly one threshold")
      if re.compile(".*within.*").match(self.bin_type):
         verif.util.error("A 'within' bin type cannot be used in this diagram")
      threshold = self.thresholds[0]
      labels = data.get_legend()

      edges = np.linspace(0, 1, self._num_bins + 1)

      var = verif.field.Threshold(threshold)

      F = data.num_inputs
      y1 = np.nan * np.zeros([F, len(edges) - 1], 'float')
      y0 = np.nan * np.zeros([F, len(edges) - 1], 'float')
      n = np.zeros([F, len(edges) - 1], 'float')
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         [obs, p] = data.get_scores([verif.field.Obs(), var], f, verif.axis.No())

         obs = verif.util.apply_threshold(obs, self.bin_type, threshold)
         p = verif.util.apply_threshold_prob(p, self.bin_type, threshold)

         clim = np.mean(obs)
         I1 = np.where(obs == 1)[0]
         I0 = np.where(obs == 0)[0]
         # Compute frequencies
         for i in range(0, len(edges) - 1):
            y0[f, i] = np.mean((p[I0] >= edges[i]) & (p[I0] < edges[i + 1]))
            y1[f, i] = np.mean((p[I1] >= edges[i]) & (p[I1] < edges[i + 1]))

         # Figure out where to put the bars. Each file will have pairs of
         # bars, so try to space them nicely.
         width = 1.0 / self._num_bins
         space = 1.0 / self._num_bins * 0.2
         shift = (0.5 / self._num_bins - width)
         center = (edges[0:-1]+edges[1:])/2
         clustercenter = edges[0:-1] + 1.0*(f + 1) / (F + 1) * width
         clusterwidth = width * 0.8 / F
         barwidth = clusterwidth / 2
         shift = barwidth
         label0 = labels[f] + " not observed"
         label1 = labels[f] + " observed"
         mpl.bar(clustercenter, y0[f, :], barwidth, color="w", ec=color, lw=self.lw, label=label0)
         mpl.bar(clustercenter-shift, y1[f, :], barwidth, color=color, ec=color, lw=self.lw, label=label1)
      mpl.plot([clim, clim], [0, 1], "k-")

      mpl.xlim([0, 1])
      mpl.xlabel("Forecasted probability")
      mpl.ylabel("Frequency")
      units = " " + data.variable.units
      middle = verif.util.get_threshold_string(self.bin_type)
      mpl.title("Discrimination diagram for obs " + middle + " " + str(threshold) + units)


class Reliability(Output):
   description = "Reliability diagram for a certain threshold (-r)"
   supports_x = False
   leg_loc = "lower right"

   def __init__(self):
      Output.__init__(self)
      self._minCount = 5  # Min number of valid data points to show in graph

   def _show_count(self):
      return not self.simple

   def _shade_confidence(self):
      return not self.simple

   def _shade_no_skill(self):
      return not self.simple

   def _plot_core(self, data):
      if self.thresholds is None or len(self.thresholds) != 1:
         verif.util.error("Reliability plot needs a single threshold (use -r)")
      if re.compile(".*within.*").match(self.bin_type):
         verif.util.error("A 'within' bin type cannot be used in this diagram")
      threshold = self.thresholds[0]   # Observation threshold
      labels = data.get_legend()

      F = data.num_inputs
      ax = mpl.gca()
      if self._show_count():
         axi = mpl.axes([0.3, 0.65, 0.2, 0.2])
      mpl.sca(ax)

      for t in range(0, len(self.thresholds)):
         threshold = self.thresholds[t]
         var = verif.field.Threshold(threshold)
         [obs, p] = data.get_scores([verif.field.Obs(), var], 0, verif.axis.No())

         # Determine the number of bins to use # (at least 11, at most 25)
         N = min(25, max(11, int(len(obs) / 1000)))
         N = 11
         edges = np.linspace(0, 1, N + 1)
         edges = np.array([0, 0.05, 0.15, 0.25, 0.35, 0.45,
            0.55, 0.65, 0.75, 0.85, 0.95, 1])
         x = np.zeros([len(edges) - 1, F], 'float')

         y = np.nan * np.zeros([F, len(edges) - 1], 'float')
         n = np.zeros([F, len(edges) - 1], 'float')
         v = np.zeros([F, len(edges) - 1], 'float')  # Variance
         # Draw reliability lines
         for f in range(0, F):
            color = self._get_color(f, F)
            style = self._get_style(f, F)
            [obs, p] = data.get_scores([verif.field.Obs(), var], f, verif.axis.No())

            obs = verif.util.apply_threshold(obs, self.bin_type, threshold)
            p = verif.util.apply_threshold_prob(p, self.bin_type, threshold)

            clim = np.mean(obs)
            # Compute frequencies
            for i in range(0, len(edges) - 1):
               q = (p >= edges[i]) & (p < edges[i + 1])
               I = np.where(q)[0]
               if len(I) > 0:
                  n[f, i] = len(obs[I])
                  # Need at least 10 data points to be valid
                  if n[f, i] >= self._minCount:
                     y[f, i] = np.mean(obs[I])
                     v[f, i] = np.var(obs[I])
                  x[i, f] = np.mean(p[I])

            label = labels[f]
            if not t == 0:
               label = ""
            mpl.plot(x[:, f], y[f], style, color=color, lw=self.lw,
                  ms=self.ms, label=label)

         # Draw confidence bands (do this separately so that these lines don't
         # sneak into the legend)
         for f in range(0, F):
            color = self._get_color(f, F)
            if self._shade_confidence():
               self._plot_confidence(x[:, f], y[f], v[f], n[f], color=color)

         # Draw lines in inset diagram
         if self._show_count():
            if np.max(n) > 1:
               for f in range(0, F):
                  color = self._get_color(f, F)
                  axi.plot(x[:, f], n[f], style, color=color, lw=self.lw,
                        ms=self.ms * 0.75)
               axi.xaxis.set_major_locator(mpl.NullLocator())
               axi.set_yscale('log')
               axi.set_title("Number")
               axi.grid('on')
      mpl.sca(ax)
      self._plot_obs([0, 1], [0, 1], label="")
      mpl.axis([0, 1, 0, 1])
      color = "gray"
      # Climatology line
      mpl.plot([0, 1], [clim, clim], "--", color=color, label="")
      mpl.plot([clim, clim], [0, 1], "--", color=color)
      # No-skill line
      mpl.plot([0, 1], [clim / 2, 1 - (1 - clim) / 2], "--", color=color)
      if self._shade_no_skill():
         verif.util.fill([clim, 1], [0, 0], [clim, 1 - (1 - clim) / 2],
               col=[1, 1, 1], zorder=-100, hatch="\\")
         verif.util.fill([0, clim], [clim / 2, clim, 0], [1, 1],
               col=[1, 1, 1], zorder=-100, hatch="\\")
      mpl.xlabel("Forecasted probability")
      mpl.ylabel("Observed frequency")
      units = " " + data.variable.units
      middle = verif.util.get_threshold_string(self.bin_type)
      mpl.title("Reliability diagram for obs " + middle + " " + str(threshold) + units)
      mpl.gca().set_aspect(1)


class IgnContrib(Output):
   description = "Binary Ignorance contribution diagram for a single "\
         "threshold (-r). Shows how much each probability issued contributes "\
         "to the total ignorance."
   supports_x = False
   leg_loc = "upper center"

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      labels = data.get_legend()

      if self.thresholds is None or len(self.thresholds) != 1:
         verif.util.error("IgnContrib diagram requires exactly one threshold")
      if re.compile(".*within.*").match(self.bin_type):
         verif.util.error("A 'within' bin type cannot be used in this diagram")
      threshold = self.thresholds[0]

      F = data.num_inputs

      mpl.subplot(2, 1, 1)
      units = " " + data.variable.units
      middle = verif.util.get_threshold_string(self.bin_type)
      mpl.title("Ignorance contribution diagram for obs " + middle + " " + str(threshold) + units)

      mpl.subplot(2, 1, 1)
      var = verif.field.Threshold(threshold)
      [obs, p] = data.get_scores([verif.field.Obs(), var], 0, verif.axis.No())

      # Determine the number of bins to use # (at least 11, at most 25)
      N = min(25, max(11, int(len(obs) / 1000)))
      edges = np.linspace(0, 1, N + 1)

      x = np.nan * np.zeros([F, len(edges) - 1], 'float')
      y = np.nan * np.zeros([F, len(edges) - 1], 'float')
      n = np.zeros([F, len(edges) - 1], 'float')

      # Draw reliability lines
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         [obs, p] = data.get_scores([verif.field.Obs(), var], f, verif.axis.No())

         obs = verif.util.apply_threshold(obs, self.bin_type, threshold)
         p = verif.util.apply_threshold_prob(p, self.bin_type, threshold)

         clim = np.mean(obs)
         # Compute frequencies
         for i in range(0, len(edges) - 1):
            q = (p >= edges[i]) & (p < edges[i + 1])
            I = np.where(q)[0]
            if len(I) > 0:
               n[f, i] = len(obs[I])
               x[f, i] = np.mean(p[I])
               # Need at least 10 data points to be valid
               if n[f, i] >= 1:
                  I0 = np.where(obs[I] == 0)
                  I1 = np.where(obs[I] == 1)
                  y[f, i] = -np.sum(np.log2(p[I[I1]])) -\
                             np.sum(np.log2(1 - p[I[I0]]))

         label = labels[f]
         mpl.plot(x[f], y[f] / np.sum(n[f]) * len(n[f]), style, color=color,
               lw=self.lw, ms=self.ms, label=label)
      mpl.ylabel("Ignorance contribution")

      # Draw expected sharpness
      xx = np.linspace(0.01, 0.99, 100)
      yy = -(xx * np.log2(xx) + (1 - xx) * np.log2(1 - xx))
      mpl.plot(xx, yy, "--", color="gray")
      yy = -np.log2(clim) * np.ones(len(xx))

      # Show number in each bin
      mpl.subplot(2, 1, 2)
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         mpl.plot(x[f], n[f], style, color=color, lw=self.lw, ms=self.ms)
      mpl.xlabel("Forecasted probability")
      mpl.ylabel("N")

      # Switch back to top subpplot, so the legend works
      mpl.subplot(2, 1, 1)

   def _adjust_axes(self, data):
      # Apply adjustements to all subplots
      for ax in mpl.gcf().get_axes():
         self._adjust_axis(ax)

      # Margins
      mpl.gcf().subplots_adjust(bottom=self.bottom, top=self.top, left=self.left, right=self.right)


class EconomicValue(Output):
   description = "Economic value diagram for a single "\
         "threshold (-r). Shows what fraction of costs/loses can be reduced by"\
         " the forecast relative to using climatology."
   supports_x = False

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      labels = data.get_legend()

      if self.thresholds is None or len(self.thresholds) != 1:
         verif.util.error("Economic value diagram requires exactly one threshold")
      if re.compile(".*within.*").match(self.bin_type):
         verif.util.error("A 'within' bin type cannot be used in this diagram")
      threshold = self.thresholds[0]

      F = data.num_inputs

      units = " " + data.variable.units
      middle = verif.util.get_threshold_string(self.bin_type)
      mpl.title("Economic value for obs " + middle + " " + str(self.thresholds[0]) + units)

      var = verif.field.Threshold(threshold)
      [obs, p] = data.get_scores([verif.field.Obs(), var], 0, verif.axis.No())

      # Determine the number of bins to use # (at least 11, at most 25)
      N = min(25, max(11, int(len(obs) / 1000)))
      N = 20
      costLossRatios = np.linspace(0, 1, N + 1)
      # import scipy.stats
      # costLossRatios = scipy.stats.norm(0,1).cdf(np.linspace(-5,5,N))
      costLossRatios = np.linspace(0, 1, N + 1)**3

      x = costLossRatios
      y = np.nan * np.zeros([F, len(costLossRatios)], 'float')
      n = np.zeros([F, len(costLossRatios)], 'float')

      # Draw reliability lines
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         [obs, p] = data.get_scores([verif.field.Obs(), var], f, verif.axis.No())

         obs = verif.util.apply_threshold(obs, self.bin_type, threshold)
         p = verif.util.apply_threshold_prob(p, self.bin_type, threshold)

         clim = np.mean(obs)
         # Compute frequencies
         for i in range(0, len(costLossRatios)):
            costLossRatio = costLossRatios[i]
            Icost = np.where(p >= costLossRatio)[0]
            Iloss = np.where((p < costLossRatio) & (obs == 1))[0]
            loss = 1
            cost = costLossRatio * loss
            totalCost = cost * len(Icost) + loss * len(Iloss)
            totalCost = totalCost / len(obs)

            # Cost when using a climatological forecast
            climCost = min(clim * loss, cost)
            perfectCost = clim * cost
            economicValue = 0
            if climCost != perfectCost:
               economicValue = (climCost-totalCost) / (climCost - perfectCost)
            y[f, i] = economicValue

         label = labels[f]
         mpl.plot(costLossRatios, y[f], style, color=color,
               lw=self.lw, ms=self.ms, label=label)
      mpl.xlabel("Cost-loss ratio")
      mpl.ylabel("Economic value")
      mpl.xlim([0, 1])
      mpl.ylim([0, 1])


class Roc(Output):
   description = "Plots the receiver operating characteristics curve for a single threshold (-r)"
   supports_x = False

   def __init__(self):
      Output.__init__(self)

   def _label_quantiles(self):
      return not self.simple

   def _plot_core(self, data):
      if self.thresholds is None or len(self.thresholds) != 1:
         verif.util.error("Roc plot needs a threshold (use -r)")
      threshold = self.thresholds[0]

      q_fields = [verif.field.Quantile(i) for i in data.quantiles]
      quantiles = data.quantiles
      if len(quantiles) == 0:
         verif.util.error("Your files do not have any quantiles")

      F = data.num_inputs
      labels = data.get_legend()
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         scores = data.get_scores([verif.field.Obs()] + q_fields, f, verif.axis.No())
         obs = scores[0]
         fcsts = scores[1:]
         y = np.nan * np.zeros([len(quantiles)], 'float')
         x = np.nan * np.zeros([len(quantiles)], 'float')
         for i in range(0, len(quantiles)):
            # Compute the hit rate and false alarm rate by using the given
            # quantile from the distribution as the forecast
            fcst = fcsts[i]
            a = np.ma.sum((fcst >= threshold) & (obs >= threshold))  # Hit
            b = np.ma.sum((fcst >= threshold) & (obs < threshold))   # FA
            c = np.ma.sum((fcst < threshold) & (obs >= threshold))   # Miss
            d = np.ma.sum((fcst < threshold) & (obs < threshold))    # CR
            if a + c > 0 and b + d > 0:
               y[i] = a / 1.0 / (a + c)
               x[i] = b / 1.0 / (b + d)
         # Add end points at 0,0 and 1,1:
         xx = x
         yy = y
         x = np.zeros([len(quantiles) + 2], 'float')
         y = np.zeros([len(quantiles) + 2], 'float')
         x[1:-1] = xx
         y[1:-1] = yy
         x[0] = 0
         y[0] = 0
         x[len(x) - 1] = 1
         y[len(y) - 1] = 1
         mpl.plot(x, y, style, color=color, label=labels[f], lw=self.lw, ms=self.ms)
         if self._label_quantiles():
            for i in range(0, len(quantiles)):
               mpl.text(x[i + 1], y[i + 1], " %g%%" % quantiles[i], verticalalignment='center')
      mpl.plot([0, 1], [0, 1], color="k")
      mpl.axis([0, 1, 0, 1])
      mpl.xlabel("False alarm rate")
      mpl.ylabel("Hit rate")
      self._plot_perfect_score([0, 0, 1], [0, 1, 1])
      units = " " + data.variable.units
      mpl.title("Threshold: " + str(threshold) + units)


# doClassic: Use the classic definition, by not varying the forecast threshold
#            i.e. using the same threshold for observation and forecast.
class DRoc(Output):
   description = "Plots the receiver operating characteristics curve for "\
         "the deterministic forecast for a single threshold. Uses different "\
         "forecast thresholds to create points."
   supports_x = False

   def __init__(self, fthresholds=None, doNorm=False, doClassic=False):
      Output.__init__(self)
      self._doNorm = doNorm
      self._fthresholds = fthresholds
      self._doClassic = doClassic

   def _show_thresholds(self):
      return not self.simple

   def _plot_core(self, data):
      if self.thresholds is None or len(self.thresholds) != 1:
         verif.util.error("DRoc plot needs a single threshold (use -r)")
      threshold = self.thresholds[0]   # Observation threshold

      if self._doClassic:
         f_thresholds = [threshold]
      else:
         if self._fthresholds is not None:
            f_thresholds = self._fthresholds
         else:
            if data.variable.name == "Precip":
               f_thresholds = [0, 1e-7, 1e-6, 1e-5, 1e-4, 0.001, 0.005,
                     0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1, 2, 3, 5, 10, 20, 100]
            else:
               N = 31
               f_thresholds = np.linspace(threshold - 10, threshold + 10, N)

      F = data.num_inputs
      labels = data.get_legend()
      f_intervals = verif.util.get_intervals(self.bin_type, f_thresholds)
      interval = verif.util.get_intervals(self.bin_type, [threshold])[0]
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f)

         y = np.nan * np.zeros([len(f_intervals), 1], 'float')
         x = np.nan * np.zeros([len(f_intervals), 1], 'float')
         for i in range(0, len(f_intervals)):
            f_interval = f_intervals[i]
            x[i] = verif.metric.Fa().compute_from_obs_fcst(obs, fcst, interval, f_interval)
            y[i] = verif.metric.Hit().compute_from_obs_fcst(obs, fcst, interval, f_interval)
         if self._doNorm:
             x = scipy.stats.norm.ppf(x)
             y = scipy.stats.norm.ppf(y)
         for i in range(0, len(f_intervals)):
            if self._show_thresholds() and (not np.isnan(x[i]) and not np.isnan(y[i])):
               mpl.text(x[i], y[i], "%2.1f" % f_intervals[i].center, color=color)
         if not self._doNorm:
            # Add end points at 0,0 and 1,1:
            xx = x
            yy = y
            x = np.zeros([len(f_intervals) + 2, 1], 'float')
            y = np.zeros([len(f_intervals) + 2, 1], 'float')
            x[1:-1] = xx
            y[1:-1] = yy
            x[0] = 1
            y[0] = 1
            x[len(x) - 1] = 0
            y[len(y) - 1] = 0
         mpl.plot(x, y, style, color=color, label=labels[f], lw=self.lw, ms=self.ms)
      if self._doNorm:
         xlim = mpl.xlim()
         ylim = mpl.ylim()
         q0 = max(abs(xlim[0]), abs(ylim[0]))
         q1 = max(abs(xlim[1]), abs(ylim[1]))
         mpl.plot([-q0, q1], [-q0, q1], 'k--')
         mpl.xlabel("Normalized false alarm rate")
         mpl.ylabel("Normalized hit rate")
      else:
         mpl.plot([0, 1], [0, 1], color="k")
         mpl.axis([0, 1, 0, 1])
         mpl.xlabel("False alarm rate")
         mpl.ylabel("Hit rate")
         self._plot_perfect_score([0, 0, 1], [0, 1, 1])
      units = " " + data.variable.units
      mpl.title("Threshold: " + str(threshold) + units)


class DRocNorm(DRoc):
   description = "Same as DRoc, except the hit and false alarm rates are transformed using the " \
            "inverse of the standard normal distribution in order to highlight the extreme " \
            "values."

   def __init__(self):
      DRoc.__init__(self, doNorm=True)


class DRoc0(DRoc):
   description = "Same as DRoc, except don't use different forecast thresholds: Use the "\
      "same\n threshold for forecast and obs."

   def __init__(self):
      DRoc.__init__(self, doNorm=False, doClassic=True)


class Against(Output):
   description = "Plots the forecasts for each pair of input files against each other. "\
   "Colours indicate which input file had the best forecast (but only if the difference is "\
   "more than 10% of the standard deviation of the observation)."
   default_axis = verif.axis.No()
   supports_threshold = False
   supports_x = False
   # How big difference should colour kick in (in number of STDs)?
   _min_std_diff = 0.1

   def _plot_core(self, data):
      F = data.num_inputs
      if F < 2:
         verif.util.error("Cannot use Against plot with less than 2 input files")

      labels = data.get_legend()
      for f0 in range(0, F):
         for f1 in range(0, F):
            if f0 != f1 and (F != 2 or f0 == 0):
               if F > 2:
                  mpl.subplot(F, F, f0 + f1 * F + 1)
               x = data.get_scores(verif.field.Fcst(), f0, verif.axis.No())
               y = data.get_scores(verif.field.Fcst(), f1, verif.axis.No())
               lower = min(min(x), min(y))
               upper = max(max(x), max(y))

               # Plot all points (including ones with missing obs)
               mpl.plot(x, y, "x", mec="k", ms=self.ms / 2, mfc="k", zorder=-10)

               # Show which forecast is better, plot on top of missing
               [obsx, x] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f0, verif.axis.No())
               [obsy, y] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f1, verif.axis.No())
               obs = obsx

               mpl.plot(x, y, "s", mec="k", ms=self.ms / 2, mfc="w", zorder=-5)

               std = np.std(obs) / 2
               minDiff = self._min_std_diff * std
               if len(x) == len(y):
                  N = 5
                  for k in range(0, N):
                     Ix = abs(obs - y) > abs(obs - x) + std * k / N
                     Iy = abs(obs - y) + std * k / N < abs(obs - x)
                     alpha = k / 1.0 / N
                     mpl.plot(x[Ix], y[Ix], "r.", ms=self.ms, alpha=alpha)
                     mpl.plot(x[Iy], y[Iy], "b.", ms=self.ms, alpha=alpha)

               mpl.xlabel(labels[f0], color="r")
               mpl.ylabel(labels[f1], color="b")
               lims = verif.util.get_square_axis_limits(mpl.xlim(), mpl.ylim())
               mpl.xlim(lims)
               mpl.ylim(lims)
               mpl.plot(lims, lims, '--', color=[0.3, 0.3, 0.3], lw=3, zorder=100)
               if F == 2:
                  break
            mpl.gca().set_aspect(1)

   def _legend(self, data, names=None):
      pass

   def _adjust_axes(self, data):
      # Apply adjustements to all subplots
      for ax in mpl.gcf().get_axes():
         self._adjust_axis(ax)

      # Margins
      mpl.gcf().subplots_adjust(bottom=self.bottom, top=self.top, left=self.left, right=self.right)


class Taylor(Output):
   description = "Taylor diagram showing correlation and forecast standard deviation. Use '-x none' to collapse all data showing only one point.  Otherwise, the whole graph is normalized by the standard deviation of the observations."
   supports_threshold = True
   supports_x = True
   leg_loc = "upper left"

   def _plot_core(self, data):
      labels = data.get_legend()
      F = data.num_inputs

      # Plot points
      maxstd = 0
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F, False)

         size = data.get_axis_size(self.axis)
         corr = np.zeros(size, 'float')
         std = np.zeros(size, 'float')
         stdobs = np.zeros(size, 'float')
         for i in range(0, size):
            [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f, self.axis, i)
            if len(obs) > 0 and len(fcst) > 0:
               corr[i] = np.corrcoef(obs, fcst)[1, 0]
               std[i] = np.sqrt(np.var(fcst))
               stdobs[i] = np.sqrt(np.var(obs))
         # Normalize
         if size > 1:
            std = std / stdobs
            stdobs = 1.0
            xlabel = "Normalized standard deviation"
            crmseLabel = "Norm CRMSE"
            minCrmseLabel = "Min norm CRMSE"
         else:
            stdobs = verif.util.nanmean(stdobs)
            xlabel = "Standard deviation (" + data.variable.units + ")"
            crmseLabel = "CRMSE"
            minCrmseLabel = "Min CRMSE"

         maxstd = max(maxstd, max(std))
         ang = np.arccos(corr)
         x = std * np.cos(ang)
         y = std * np.sin(ang)
         mpl.plot(x, y, style, color=color, label=labels[f], lw=self.lw,
               ms=self.ms)

      # Set axis limits
      # Enforce a minimum radius beyond the obs-radius
      if maxstd < 1.25 * stdobs:
         maxstd = 1.25 * stdobs
      maxstd = int(np.ceil(maxstd))
      if self.xlim is not None:
         maxstd = self.xlim[1]
      # Allow for some padding outside the outer ring
      mpl.xlim([-maxstd * 1.05, maxstd * 1.05])
      mpl.ylim([0, maxstd * 1.05])
      xticks = mpl.xticks()[0]
      mpl.xticks(xticks[xticks >= 0])
      mpl.xlim([-maxstd * 1.05, maxstd * 1.05])
      mpl.ylim([0, maxstd * 1.05])

      # Correlation
      mpl.text(np.sin(np.pi / 4) * maxstd, np.cos(np.pi / 4) * maxstd,
            "Correlation", rotation=-45, fontsize=self.labfs,
            horizontalalignment="center", verticalalignment="bottom")
      corrs = [-1, -0.99, -0.95, -0.9, -0.8, -0.5, 0, 0.5, 0.8, 0.9, 0.95, 0.99]
      for i in range(0, len(corrs)):
         ang = np.arccos(corrs[i])  # Mathematical angle
         x = np.cos(ang) * maxstd
         y = np.sin(ang) * maxstd
         if self.xlim is None or x >= self.xlim[0]:
            mpl.plot([0, x], [0, y], 'k--')
            mpl.text(x, y, str(corrs[i]), verticalalignment="bottom", fontsize=self.labfs)

      # Draw vertical bouning line if lower xlim is 0
      if self.xlim is not None and self.xlim[0] == 0:
         mpl.plot([0, 0], [0, maxstd], 'k-')

      mpl.gca().yaxis.set_visible(False)
      # Remove box around plot
      mpl.gca().spines['bottom'].set_visible(False)
      mpl.gca().spines['top'].set_visible(False)
      mpl.gca().spines['left'].set_visible(False)
      mpl.gca().spines['right'].set_visible(False)
      mpl.gca().xaxis.set_ticks_position('bottom')
      mpl.xlabel(xlabel)

      # Draw obs point/lines
      orange = [1, 0.8, 0.4]
      self._draw_circle(stdobs, style='-', lw=5, color=orange)
      mpl.plot(stdobs, 0, 's-', color=orange, label="Observed", mew=2, ms=self.ms, clip_on=False)

      # Draw CRMSE rings
      xticks = mpl.xticks()[0]
      self._draw_circle(0, style="-", color="gray", lw=3, label=crmseLabel)
      Rs = np.linspace(0, 2 * max(xticks), 4 * max(xticks) / (xticks[1] -
         xticks[0]) + 1)
      for R in Rs:
         if R > 0:
            self._draw_circle(R, xcenter=stdobs, ycenter=0, maxradius=maxstd, style="-", color="gray", lw=3)
            x = stdobs
            y = np.cos(np.pi / 4) * R
            if x ** 2 + y ** 2 < maxstd ** 2:
               mpl.text(x, y, str(R), horizontalalignment="right",
                     verticalalignment="bottom", fontsize=self.labfs,
                     color="gray")

      # Draw minimum CRMSE
      self._draw_circle(stdobs/2, xcenter=stdobs/2, ycenter=0, style="--",
            color="orange", lw=3, label=minCrmseLabel, zorder=0)

      # Draw std rings
      for X in mpl.xticks()[0]:
         if X <= maxstd:
            self._draw_circle(X, style=":")
      self._draw_circle(maxstd, style="-", lw=3)

      # Draw bottom line
      mpl.plot([-maxstd, maxstd], [0, 0], "k-", lw=3)
      mpl.gca().set_aspect(1)


class Performance(Output):
   description = "Categorical performance diagram showing POD, FAR, bias, and Threat score. Also shows the scores the forecasts would attain by using different forecast thresholds (turn off using -simple)"
   supports_x = True
   leg_loc = "upper left"
   reference = "Roebber, P.J., 2009: Visualizing multiple measures of forecast quality. Wea. Forecasting, 24, 601-608."

   def _show_potential(self):
      """ Should lines be drawn to show how the scores can vary with chosen forecast threshold? """
      return not self.simple

   def _plot_core(self, data):
      if self.thresholds is None or len(self.thresholds) != 1:
         verif.util.error("Performance plot needs a single threshold (use -r)")
      threshold = self.thresholds[0]   # Observation threshold
      labels = data.get_legend()
      F = data.num_inputs
      interval = verif.util.get_intervals(self.bin_type, [threshold])[0]
      num_max_points = 20

      # Plot points
      maxstd = 0
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F, False)

         size = data.get_axis_size(self.axis)
         for t in range(0, len(self.thresholds)):
            threshold = self.thresholds[t]
            sr = np.zeros(size, 'float')
            pod = np.zeros(size, 'float')
            Far = verif.metric.Far()
            Hit = verif.metric.Hit()
            for i in range(0, size):
               [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f, self.axis, i)
               f_intervals = self._get_f_intervals(fcst, self.bin_type, num_max_points)
               J = len(f_intervals)

               fa = Far.compute_from_obs_fcst(obs, fcst, interval)
               hit = Hit.compute_from_obs_fcst(obs, fcst, interval)
               sr[i] = 1 - fa
               pod[i] = hit

               # Compute the potential that the forecast can attan by using
               # different forecast thresholds
               if self._show_potential():
                  x = np.zeros(J, 'float')
                  y = np.zeros(J, 'float')
                  for j in range(0, J):
                     x[j] = 1 - Far.compute_from_obs_fcst(obs, fcst, interval, f_intervals[j])
                     y[j] = Hit.compute_from_obs_fcst(obs, fcst, interval, f_intervals[j])
                  mpl.plot(x, y, ".-", color=color, ms=3*self.lw, lw=2*self.lw, zorder=-100, alpha=0.3)

            label = ""
            if t == 0:
               label = labels[f]
            mpl.plot(sr, pod, style, color=color, label=label, lw=self.lw, ms=self.ms)

      # Plot bias lines
      biases = [0.3, 0.5, 0.8, 1, 1.3, 1.5, 2, 3, 5, 10]
      for i in range(0, len(biases)):
         bias = biases[i]
         label = ""
         if i == 0:
            label = "Bias frequency"
         mpl.plot([0, 1], [0, bias], 'k-', label=label)
         if bias <= 1:
            mpl.text(1, bias, "%2.1f" % (bias))
         else:
            mpl.text(1.0/bias, 1, "%2.1f" % (bias))

      # Plot threat score lines
      threats = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
      for i in range(0, len(threats)):
         threat = threats[i]
         x = np.linspace(threat, 1, 100)
         label = ""
         if i == 0:
            label = "Threat score"
         y = 1.0 / (1 + 1.0/threat - 1.0 / x)
         mpl.plot(x, y, 'k--', label=label)
         xx = 2.0 / (1 + 1.0/threat)
         mpl.text(xx, xx, str(threat))

      mpl.xlabel("Success ratio (1 - FAR)")
      mpl.ylabel("Probability of detection")
      mpl.xlim([0, 1])
      mpl.ylim([0, 1])
      mpl.gca().set_aspect(1)

   @staticmethod
   def _get_f_intervals(fcst, bin_type, num_max):
      percentiles = np.linspace(0, 100, num_max)
      f_thresholds = np.array([np.percentile(np.unique(np.sort(fcst)), p) for p in percentiles])
      # put a point in forecast point (so that the line goes
      # through the point
      f_thresholds = np.unique(np.sort(np.append(f_thresholds, 0)))
      # alternatively, nudge the closest point to 0
      # iclosest = np.argmin(np.abs(dx))
      # dx[iclosest] = 0
      f_intervals = verif.util.get_intervals(bin_type, f_thresholds)
      return f_intervals


class Error(Output):
   description = "Decomposition of RMSE into systematic and unsystematic components"
   supports_threshold = False
   supports_x = False
   default_axis = verif.axis.No()

   def _plot_core(self, data):
      labels = data.get_legend()
      F = data.num_inputs

      mpl.gca().set_aspect(1)
      mpl.xlabel("Unsystematic error (CRMSE, " + data.variable.units + ")")
      mpl.ylabel("Systematic error (Bias, " + data.variable.units + ")")

      # Plot points
      size = data.get_axis_size(self.axis)
      serr = np.nan * np.zeros([size, F], 'float')
      uerr = np.nan * np.zeros([size, F], 'float')
      rmse = np.nan * np.zeros([size, F], 'float')
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F, connectingLine=False)

         for i in range(0, size):
            [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f, self.axis, i)
            mfcst = np.mean(fcst)
            mobs = np.mean(obs)
            if len(obs) > 0 and len(fcst) > 0:
               serr[i, f] = np.mean(obs - fcst)
               rmse[i, f] = np.sqrt(np.mean((obs - fcst) ** 2))
               uerr[i, f] = np.sqrt(rmse[i, f] ** 2 - serr[i, f] ** 2)
         mpl.plot(uerr[:, f], serr[:, f], style, color=color, label=labels[f],
               lw=self.lw, ms=self.ms)
      xlim = mpl.xlim()
      ylim = mpl.ylim()

      # Draw rings
      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F, lineOnly=True)
         self._draw_circle(verif.util.nanmean(rmse[:, f]), style=style, color=color)

      # Set axis limits
      maxx = xlim[1]
      maxy = ylim[1]
      miny = min(0, ylim[0])
      # Try to enforce the x-axis and y-axis to be roughly the same size
      if maxy - miny < maxx / 2:
         maxy = maxx
      elif maxy - miny > maxx * 2:
         maxx = maxy - miny
      mpl.xlim([0, maxx])  # Not possible to have negative CRMSE
      mpl.ylim([miny, maxy])

      # Draw standard RMSE rings
      for X in mpl.xticks()[0]:
         self._draw_circle(X, style=":")

      mpl.plot([0, maxx], [0, 0], 'k-', lw=2)  # Draw x-axis line


class Marginal(Output):
   description = "Show marginal distribution for different thresholds"
   require_threshold_type = "threshold"
   supports_x = False

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      labels = data.get_legend()

      F = data.num_inputs

      clim = np.zeros(len(self.thresholds), 'float')
      for f in range(0, F):
         x = self.thresholds
         y = np.zeros([len(self.thresholds)], 'float')
         for t in range(0, len(self.thresholds)):
            threshold = self.thresholds[t]
            var = verif.field.Threshold(threshold)
            [obs, p] = data.get_scores([verif.field.Obs(), var], f)

            obs = verif.util.apply_threshold(obs, self.bin_type, threshold)
            p = verif.util.apply_threshold_prob(p, self.bin_type, threshold)

            clim[t] = np.mean(obs)
            y[t] = np.mean(p)

         color = self._get_color(f, F)
         style = self._get_style(f, F)

         label = labels[f]
         mpl.plot(x, y, style, color=color, lw=self.lw, ms=self.ms, label=label)
      self._plot_obs(x, clim)

      mpl.ylim([0, 1])
      mpl.xlabel(verif.axis.Threshold().label(data.variable))
      mpl.ylabel("Marginal probability")


class Freq(Output):
   description = "Show frequency of obs and forecasts"
   default_bin_type = "within="
   require_threshold_type = "deterministic"
   supports_x = False

   def __init__(self):
      Output.__init__(self)

   def _plot_core(self, data):
      labels = data.get_legend()
      intervals = verif.util.get_intervals(self.bin_type, self.thresholds)
      x = [i.center for i in intervals]

      F = data.num_inputs
      N = len(intervals)

      for f in range(0, F):
         color = self._get_color(f, F)
         style = self._get_style(f, F)
         y = np.zeros(N, 'float')
         clim = np.zeros(N, 'float')
         obs = None
         fcst = None
         if verif.field.Obs() in data.get_fields() and verif.field.Fcst() in data.get_fields():
            [obs, fcst] = data.get_scores([verif.field.Obs(), verif.field.Fcst()], f, verif.axis.No())
         elif verif.field.Obs() in data.get_fields():
            obs = data.get_scores(verif.field.Obs(), f, verif.axis.No())
         elif verif.field.Fcst() in data.get_fields():
            fcst = data.get_scores(verif.field.Fcst(), f, verif.axis.No())

         for i in range(N):
            interval = intervals[i]
            if obs is not None:
               obs0 = verif.util.apply_threshold(obs, self.bin_type, interval.lower, interval.upper)
               clim[i] = np.nanmean(obs0)
            if fcst is not None:
               fcst0 = verif.util.apply_threshold(fcst, self.bin_type, interval.lower, interval.upper)
               y[i] = np.nanmean(fcst0)

         label = labels[f]
         if fcst is not None:
            mpl.plot(x, y, style, color=color, lw=self.lw, ms=self.ms, label=label)
      if obs is not None:
         self._plot_obs(x, clim)

      mpl.ylim([0, 1])
      mpl.xlabel(verif.axis.Threshold().label(data.variable))
      mpl.ylabel("Frequency " + self.bin_type)


class InvReliability(Output):
   description = "Reliability diagram for a certain quantile (-q)"
   supports_x = False

   def __init__(self):
      Output.__init__(self)

   def _show_count(self):
      return False

   def _shade_confidence(self):
      return not self.simple

   def _plot_core(self, data):
      labels = data.get_legend()
      if self.quantiles is None or len(self.quantiles) < 1:
         verif.util.error("InvReliability requires at least one quantile")

      F = data.num_inputs
      ax = mpl.gca()
      if self._show_count():
         if self.quantiles[0] < 0.5:
            axi = mpl.axes([0.66, 0.65, 0.2, 0.2])
         else:
            axi = mpl.axes([0.66, 0.15, 0.2, 0.2])
      mpl.sca(ax)

      for t in range(0, len(self.quantiles)):
         quantile = self.quantiles[t]
         var = verif.field.Quantile(quantile)
         [obs, p] = data.get_scores([verif.field.Obs(), var], 0, verif.axis.No())

         # Determine the number of bins to use # (at least 11, at most 25)
         if self.thresholds is None:
            N = min(25, max(11, int(len(obs) / 1000)))
            if data.variable.name == "Precip":
               edges = np.linspace(0, np.sqrt(verif.util.nanmax(obs)), N + 1) ** 2
            else:
               edges = np.linspace(verif.util.nanmin(obs), verif.util.nanmax(obs), N + 1)
         else:
            edges = np.array(self.thresholds)

         x = np.zeros([len(edges) - 1, F], 'float')
         y = np.nan * np.zeros([F, len(edges) - 1], 'float')
         n = np.zeros([F, len(edges) - 1], 'float')
         v = np.zeros([F, len(edges) - 1], 'float')
         # Draw reliability lines
         for f in range(0, F):
            color = self._get_color(f, F)
            style = self._get_style(f, F)
            [obs, p] = data.get_scores([verif.field.Obs(), var], f, verif.axis.No())

            obs = obs <= p

            # Compute frequencies
            for i in range(0, len(edges) - 1):
               q = (p >= edges[i]) & (p < edges[i + 1])
               I = np.where(q)[0]
               if len(I) > 0:
                  n[f, i] = len(obs[I])
                  # Need at least 10 data points to be valid
                  if n[f, i] >= 2:
                     y[f, i] = np.mean(obs[I])
                     v[f, i] = np.var(obs[I])
                  x[i, f] = np.mean(p[I])

            label = labels[f]
            if not t == 0:
               label = ""
            mpl.plot(x[:, f], y[f], style, color=color, lw=self.lw,
                  ms=self.ms, label=label)
         self._plot_obs(edges, 0 * edges + quantile, label="")

         # Draw confidence bands (do this separately so that these lines don't
         # sneak into the legend)
         for f in range(0, F):
            color = self._get_color(f, F)
            if self._shade_confidence():
               self._plot_confidence(x[:, f], y[f], v[f], n[f], color=color)
            if self._show_count():
               axi.plot(x[:, f], n[f], style, color=color, lw=self.lw, ms=self.ms)
               axi.xaxis.set_major_locator(mpl.NullLocator())
               axi.set_yscale('log')
               axi.set_title("Number")
      mpl.sca(ax)
      mpl.ylim([0, 1])
      color = "gray"
      mpl.xlabel(data.get_variable_and_units())
      mpl.ylabel("Observed frequency")
      units = " " + data.variable.units
      if len(self.quantiles) == 1:
         mpl.title("Quantile: " + str(self.quantiles[0] * 100) + "%")


class Impact(Output):
   description = ""\
   "Colours indicate which input file had the best forecast (but only if the difference is "\
   "more than 10% of the standard deviation of the observation)."
   default_axis = verif.axis.No()
   supports_threshold = False
   require_threshold_type = "deterministic"
   supports_x = False
   _showNumbers = False
   _prob = False

   def _plot_core(self, data):
      F = data.num_inputs
      units = data.variable.units
      if F != 2:
         verif.util.error("Improvement plot requires exactly 2 files")

      if self.thresholds is None or len(self.thresholds) < 2:
         verif.util.error("Reliability plot needs at least two thresholds (use -r)")

      labels = data.get_legend()
      edges = self.thresholds

      # Show which forecast is better
      fcstField = verif.field.Fcst()
      p = 0.5
      if self._prob:
         fcstField = verif.field.Quantile(p)
      [obsx, x] = data.get_scores([verif.field.Obs(), fcstField], 0)
      [obsy, y] = data.get_scores([verif.field.Obs(), fcstField], 1)
      x = x.flatten()
      y = y.flatten()
      obs = obsx.flatten()
      if self._prob:
         obs = obs <= p

      w = (edges[1]-edges[0])/2
      centres = (edges[1:] + edges[0:-1]) / 2
      error_x = abs(x - obs)**2
      error_y = abs(y - obs)**2

      XX = np.repeat(centres, len(centres))
      YY = np.tile(centres, len(centres))
      contrib = np.zeros([len(XX)], float)
      num = np.zeros([len(XX)], float)

      for e in range(0, len(XX)):
         I = np.where((x > XX[e] - w) & (x <= XX[e] + w) &
                      (y > YY[e] - w) & (y <= YY[e] + w))[0]
         if len(I) > 0:
            contrib[e] = np.nansum(error_x[I] - error_y[I])
            num[e] = len(I)
      I0 = np.where(contrib < 0)[0]
      I1 = np.where(contrib > 0)[0]
      # Compute size (scatter wants area) of marker. Scale using self.ms.
      S = 400/np.max(contrib**2) * (self.ms / 8.0)**2
      mpl.scatter(XX[I0], YY[I0], s=abs(contrib[I0]**2)*S,
            color="red", label="%s is better" % labels[0])
      mpl.scatter(XX[I1], YY[I1], s=abs(contrib[I1]**2)*S,
            color="blue", label="%s is better" % labels[1])
      if self._showNumbers:
         Snum = 400/np.max(num**2)
         mpl.scatter(XX, YY, s=abs(num**2) * Snum, edgecolor="k",
               color=[1, 1, 1, 0], lw=1, zorder=100)

      xlim = mpl.xlim()
      ylim = mpl.ylim()
      lower = min(xlim[0], ylim[0])
      upper = max(xlim[1], ylim[1])
      mpl.xlim([lower, upper])
      mpl.ylim([lower, upper])
      mpl.xlabel("%s (%s)" % (labels[0], units), color="r")
      mpl.ylabel("%s (%s)" % (labels[1], units), color="b")

      # Draw diagonal
      lims = verif.util.get_square_axis_limits(mpl.xlim(), mpl.ylim())
      mpl.xlim(lims)
      mpl.ylim(lims)
      self._plot_perfect_diagonal(always_show=1, label="")
      mpl.gca().set_aspect(1)

   def _legend(self, data, names=None):
      if self.legfs > 0:
         if names is None:
            mpl.legend(loc=self.leg_loc, prop={'size': self.legfs})
         else:
            mpl.legend(names, loc=self.leg_loc, prop={'size': self.legfs})
