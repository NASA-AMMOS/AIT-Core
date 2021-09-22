# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2009, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""AIT 2D/3D Geometry

This module contains basic 2D and 3D geometry classes (Point, Line,
Polygon, Rectangle) with arithmetic operator, containment, and
sequence/iterator methods.  These methods allow for natural and
convenient Python expressions such as::

  # Translate point by five units in both x and y.
  point + 5

  # Polygon hit tests
  if point in polygon:
    ...

  # Iteration or vertices
  for vertex in polygon:
    ...

This module was originally written as a support library for AEGIS
ground processing code and its precursors (e.g. OASIS).  It dates back
to at least 2009 and probably even earlier.
"""


class Point(object):
    r"""Point is a simple 2D Cartesian point object with public 'x' and
    'y' coordinate fields.  The operators +, -, +=, -=, \*, \*=, /, /=, ==
    and !=.
    """

    __slots__ = ["x", "y", "z"]

    def __init__(self, x=0, y=0, z=None):
        """Point(x=0, y=0, z=None) -> Point
        Point([x, y, z])        -> Point
        Point([x, y])           -> Point
        """
        if isinstance(x, (list, tuple)):
            if len(x) >= 2:
                self.x = x[0]
                self.y = x[1]
                self.z = None
            if len(x) == 3:
                self.z = x[2]
        else:
            self.x = x
            self.y = y
            self.z = z

    def copy(self):
        """Returns a copy of this Point."""
        return Point(self.x, self.y, self.z)

    def __repr__(self):
        if self.z:
            return "Point(%s, %s, %s)" % (str(self.x), str(self.y), str(self.z))
        else:
            return "Point(%s, %s)" % (str(self.x), str(self.y))

    def __add__(self, other):
        """Adds the (x, y) coordinates of two points or a point and a
        number.  Examples:

        >>> Point(1, 2) + 1
        Point(2, 3)

        >>> Point(1, 2) + Point(3, 4)
        Point(4, 6)
        """
        if isinstance(other, Point):
            if self.z and other.z:
                return Point(self.x + other.x, self.y + other.y, self.z + other.z)
            else:
                return Point(self.x + other.x, self.y + other.y, self.z)
        else:
            if self.z:
                return Point(self.x + other, self.y + other, self.z + other)
            else:
                return Point(self.x + other, self.y + other, self.z)

    def __radd__(self, other):
        """Adds a number to the (x, y) coordinates of a point.  Examples:

        >>> 1 + Point(1, 2)
        Point(2, 3)
        """
        return self.__add__(other)

    def __sub__(self, other):
        """Subtracts the (x, y) coordinates of two points or a point and a
        number.  Examples:

        >>> Point(1, 2) - 1
        Point(0, 1)

        >>> Point(1, 2) - Point(3, 4)
        Point(-2, -2)
        """
        if isinstance(other, Point):
            if self.z and other.z:
                return Point(self.x - other.x, self.y - other.y, self.z - other.z)
            else:
                return Point(self.x - other.x, self.y - other.y, self.z)
        else:
            if self.z:
                return Point(self.x - other, self.y - other, self.z - other)
            else:
                return Point(self.x - other, self.y - other, self.z)

    def __mul__(self, other):
        """Multiplies the (x, y) coordinates of a point by a number.
        Examples:

        >>> Point(2, 3) * 0
        Point(0, 0)

        >>> Point(2, 3) * 1
        Point(2, 3)

        >>> Point(2, 3) * 2
        Point(4, 6)
        """
        if self.z:
            return Point(self.x * other, self.y * other, self.z * other)
        else:
            return Point(self.x * other, self.y * other)

    def __rmul__(self, other):
        """Multiplies the (x, y) coordinates of a point by a number."""
        return self.__mul__(other)

    def __div__(self, other):
        """Divides the (x, y) coordinates of a point by a number.
        Examples:

        >>> Point(4, 6) / 1
        Point(4, 6)

        >>> Point(4, 6) / 2
        Point(2, 3)

        >>> Point(2, 3) / 2
        Point(1, 1)

        >>> Point(2.0, 3.0) / 2
        Point(1.0, 1.5)
        """
        if self.z:
            return Point(self.x / other, self.y / other, self.z / other)
        else:
            return Point(self.x / other, self.y / other)

    def __iadd__(self, other):
        """Adds the (x, y) coordinates of two points or a point and a
        number.  Examples:

        >>> p  = Point(1, 2)
        >>> p += 1
        >>> p
        Point(2, 3)

        >>> p  = Point(1, 2)
        >>> p += Point(3, 4)
        >>> p
        Point(4, 6)
        """
        if isinstance(other, Point):
            self.x += other.x
            self.y += other.y
            if self.z and other.z:
                self.z += other.z
        else:
            self.x += other
            self.y += other
            if self.z:
                self.z += other
        return self

    def __isub__(self, other):
        """Subtracts the (x, y) coordinates of two points or a point and a
        number.  Examples:

        >>> p  = Point(1, 2)
        >>> p -= 1
        >>> p
        Point(0, 1)

        >>> p  = Point(1, 2)
        >>> p -= Point(3, 4)
        >>> p
        Point(-2, -2)
        """
        if isinstance(other, Point):
            self.x -= other.x
            self.y -= other.y
            if self.z and other.z:
                self.z -= other.z
        else:
            self.x -= other
            self.y -= other
            if self.z:
                self.z -= other
        return self

    def __imul__(self, other):
        """Multiplies the (x, y) coordinates of a point by a number.
        Examples:

        >>> p  = Point(2, 3)
        >>> p *= 0
        >>> p
        Point(0, 0)

        >>> p  = Point(2, 3)
        >>> p *= 1
        >>> p
        Point(2, 3)

        >>> p  = Point(2, 3)
        >>> p *= 2
        >>> p
        Point(4, 6)
        """
        if isinstance(other, Point):
            self.x *= other.x
            self.y *= other.y
            if self.z and other.z:
                self.z *= other.z
        else:
            self.x *= other
            self.y *= other
            if self.z:
                self.z *= other
        return self

    def __idiv__(self, other):
        """Divides the (x, y) coordinates of a point by a number.
        Examples:

        >>> p  = Point(4, 6)
        >>> p /= 1
        >>> p
        Point(4, 6)

        >>> p  = Point(4, 6)
        >>> p /= 2
        >>> p
        Point(2, 3)

        >>> p  = Point(2, 3)
        >>> p /= 2
        >>> p
        Point(1, 1)

        >>> p  = Point(2.0, 3.0)
        >>> p /= 2
        >>> p
        Point(1.0, 1.5)
        """
        if isinstance(other, Point):
            self.x /= other.x
            self.y /= other.y
            if self.z and other.z:
                self.z /= other.z
        else:
            self.x /= other
            self.y /= other
            if self.z:
                self.z /= other
        return self

    def __eq__(self, other):
        """Compares the (x, y) coordinates of two points for equality.
        Examples:

        >>> Point(8, 7) == Point(8, 7)
        True

        >>> Point(8, 7) == Point(7, 8)
        False

        >>> Point(8, 7) == None
        False
        """
        if isinstance(other, Point):
            if self.z:
                return self.x == other.x and self.y == other.y and self.z == other.z
            else:
                return self.x == other.x and self.y == other.y
        else:
            return False

    def __ne__(self, other):
        """Compare the (x, y) coordinates of two points for inequality.
        Examples:

        >>> Point(8, 7) != Point(8, 7)
        False

        >>> Point(8, 7) != Point(7, 8)
        True

        >>> Point(8, 7) != None
        True
        """
        return not self.__eq__(other)

    def __len__(self):
        """Returns the dimensionality of this Point, either 2 or 3."""
        if self.z:
            return 3
        else:
            return 2

    def __getitem__(self, key):
        """Returns the x, y, or z (0, 1, 2) coordinate of this point."""
        if key == 0:
            return self.x
        elif key == 1:
            return self.y
        elif key == 2 and self.z is not None:
            return self.z
        else:
            raise IndexError("Point index out of range")

    def __setitem__(self, key, value):
        """Sets the x, y, or z (0, 1, 2) coordinate of this point."""
        if key == 0:
            self.x = value
        elif key == 1:
            self.y = value
        elif key == 2 and self.z is not None:
            self.z = value
        else:
            raise IndexError("Point assignment index out of range")

    def dot(self, other):
        """dot (self, other) -> number

        Returns the dot product of this Point with another.
        """
        if self.z:
            return (self.x * other.x) + (self.y * other.y) + (self.z * other.z)
        else:
            return (self.x * other.x) + (self.y * other.y)


class Line(object):
    """Line segment objects contain two points."""

    __slots__ = ["p", "q"]

    def __init__(self, p, q):
        """Line(Point, Point) -> Line

        Creates a new Line segment with the given endpoints.
        """
        self.p = p
        self.q = q

    def __repr__(self):
        return "Line(%s, %s)" % (str(self.p), str(self.q))

    def slope(self):
        """slope () -> float"""
        return (self.p.y - self.q.y) / (self.p.x - self.q.x)

    def intersect(self, line):
        """intersect (line) -> Point | None

        Returns the intersection point of this line segment with another.
        If this line segment and the other line segment are conincident,
        the first point on this line segment is returned.  If the line
        segments do not intersect, None is returned.

        See http://local.wasp.uwa.edu.au/~pbourke/geometry/lineline2d/

        Examples:

        >>> A = Line( Point(0.0, 0.0), Point(5.0, 5.0) )
        >>> B = Line( Point(5.0, 0.0), Point(0.0, 5.0) )
        >>> C = Line( Point(1.0, 3.0), Point(9.0, 3.0) )
        >>> D = Line( Point(0.5, 3.0), Point(6.0, 4.0) )
        >>> E = Line( Point(1.0, 1.0), Point(3.0, 8.0) )
        >>> F = Line( Point(0.5, 2.0), Point(4.0, 7.0) )
        >>> G = Line( Point(1.0, 2.0), Point(3.0, 6.0) )
        >>> H = Line( Point(2.0, 4.0), Point(4.0, 8.0) )
        >>> I = Line( Point(3.5, 9.0), Point(3.5, 0.5) )
        >>> J = Line( Point(3.0, 1.0), Point(9.0, 1.0) )
        >>> K = Line( Point(2.0, 3.0), Point(7.0, 9.0) )
        >>> L = Line( Point(1.0, 2.0), Point(5.0, 7.0) )

        >>> A.intersect(B)
        Point(2.5, 2.5)

        >>> C.intersect(D) == None
        True

        >>> E.intersect(F)
        Point(1.8275862069, 3.89655172414)

        >>> G.intersect(H)
        Point(1.0, 2.0)

        >>> I.intersect(J)
        Point(3.5, 1.0)

        >>> K.intersect(L) == None
        True
        """
        (x1, y1) = (self.p.x, self.p.y)
        (x2, y2) = (self.q.x, self.q.y)
        (x3, y3) = (line.p.x, line.p.y)
        (x4, y4) = (line.q.x, line.q.y)
        denom = ((y4 - y3) * (x2 - x1)) - ((x4 - x3) * (y2 - y1))
        num1 = ((x4 - x3) * (y1 - y3)) - ((y4 - y3) * (x1 - x3))
        num2 = ((x2 - x1) * (y1 - y3)) - ((y2 - y1) * (x1 - x3))
        intersect = None

        if num1 == 0 and num2 == 0 and denom == 0:  # Coincident lines
            intersect = self.p
        elif denom != 0:  # Parallel lines (denom == 0)
            ua = float(num1) / denom
            ub = float(num2) / denom
            if ua >= 0.0 and ua <= 1.0 and ub >= 0.0 and ub <= 1.0:
                x = x1 + (ua * (x2 - x1))
                y = y1 + (ua * (y2 - y1))
                intersect = Point(x, y)

        return intersect


class Plane(object):
    """Plane objects are defined by a point and direction vector normal
    to the plane.
    """

    __slots__ = ["p", "n"]

    def __init__(self, point, normal):
        """Plane(point, normal) -> Plane

        Creates a new plane given a point and direction vector normal to
        the plane.
        """
        self.p = point
        self.n = normal

    def __repr__(self):
        return "Plane(point=%s, normal=%s)" % (str(self.p), str(self.n))

    def front(self, point):
        """front (point) -> True | False

        Returns True if point is in ""front"" of the Plane, False otherwise.
        """
        return self.n.dot(self.p - point) > 0

    def intersect(self, line):
        """intersect(line) -> Point | None

        Returns the point at which the line segment and Plane intersect
        or None if they do not intersect.
        """
        eps = 1e-8
        d = line.q - line.p
        dn = d.dot(self.n)
        point = None

        if abs(dn) >= eps:
            mu = self.n.dot(self.p - line.p) / dn
            if mu >= 0 and mu <= 1:
                point = line.p + mu * d

        return point


class Polygon(object):
    """Polygon objects contain a list of points."""

    __slots__ = ["_bounds", "_dirty", "vertices"]

    def __init__(self, *vertices):
        """Polygon(vertices) -> Polygon

        Creates a new Polygon with no vertices.
        """
        if vertices:
            if len(vertices) == 1 and isinstance(vertices[0], list):
                vertices = vertices[0]
            else:
                vertices = list(vertices)
        else:
            vertices = []

        if len(vertices) > 0 and isinstance(vertices[0], (list, tuple)):
            vertices = [Point(v) for v in vertices]

        self._bounds = None
        self._dirty = True
        self.vertices = vertices

    def __contains__(self, point):
        """__contains__ (self, point) -> True | False

        Allows syntax: if point in polygon
        """
        return self.contains(point)

    def __len__(self):
        """__len__ () -> integer

        Returns the number of vertices in this Polygon.

        Examples:

        >>> p = Polygon()
        >>> len(p)
        0

        >>> p.vertices = [ Point(0, 0), Point(0, 1), Point(0, 2) ]
        >>> len(p)
        3
        """
        return len(self.vertices)

    def __getitem__(self, key):
        """Returns the nth vertex of this Polygon."""
        return self.vertices[key]

    def __setitem__(self, key, value):
        """Sets the nth vertex of this Polygon."""
        self.vertices[key] = value
        self._dirty = True

    def __iter__(self):
        return self.vertices.__iter__()

    def __repr__(self):
        if len(self.vertices) > 4:
            vertices = "<len(vertices)=%d>" % len(self.vertices)
        else:
            vertices = "(" + ", ".join(str(v) for v in self.vertices) + ")"
        return "Polygon%s" % vertices

    def area(self):
        """area() -> number

        Returns the area of this Polygon.
        """
        area = 0.0

        for segment in self.segments():
            area += ((segment.p.x * segment.q.y) - (segment.q.x * segment.p.y)) / 2

        return area

    def bounds(self):
        """bounds() -> Rect

        Returns the bounding Rectangle for this Polygon.
        """
        if self._dirty:
            min = self.vertices[0].copy()
            max = self.vertices[0].copy()
            for point in self.vertices[1:]:
                if point.x < min.x:
                    min.x = point.x
                if point.y < min.y:
                    min.y = point.y
                if point.x > max.x:
                    max.x = point.x
                if point.y > max.y:
                    max.y = point.y

            self._bounds = Rect(min, max)
        self._dirty = False

        return self._bounds

    def center(self):
        """center() -> (x, y)

        Returns the center (of mass) point of this Polygon.

        See http://en.wikipedia.org/wiki/Polygon

        Examples:

        >>> p = Polygon()
        >>> p.vertices = [ Point(3, 8), Point(6, 4), Point(0, 3) ]
        >>> p.center()
        Point(2.89285714286, 4.82142857143)
        """
        Cx = 0.0  # noqa
        Cy = 0.0  # noqa
        denom = 6.0 * self.area()

        for segment in self.segments():
            x = segment.p.x + segment.q.x
            y = segment.p.y + segment.q.y
            xy = (segment.p.x * segment.q.y) - (segment.q.x * segment.p.y)
            Cx += x * xy
            Cy += y * xy

        Cx /= denom
        Cy /= denom

        return Point(Cx, Cy)

    def contains(self, p):
        """Returns True if point is contained inside this Polygon, False
        otherwise.

        This method uses the Ray Casting algorithm.

        Examples:

        >>> p = Polygon()
        >>> p.vertices = [Point(1, 1), Point(1, -1), Point(-1, -1), Point(-1, 1)]

        >>> p.contains( Point(0, 0) )
        True

        >>> p.contains( Point(2, 3) )
        False

        """
        inside = False

        if p in self.bounds():
            for s in self.segments():
                if (s.p.y > p.y) != (s.q.y > p.y) and (
                    p.x < (s.q.x - s.p.x) * (p.y - s.p.y) / (s.q.y - s.p.y) + s.p.x
                ):
                    inside = not inside

        return inside

    def segments(self):
        """Return the Line segments that comprise this Polygon."""
        for n in range(len(self.vertices) - 1):
            yield Line(self.vertices[n], self.vertices[n + 1])

        yield Line(self.vertices[-1], self.vertices[0])


class Rect(object):
    """Rect"""

    __slots__ = ["ul", "lr"]

    def __init__(self, ul, lr):
        """Rect(Point, Point) -> Rect

        Creates a new rectangle.
        """
        self.ul = Point(min(ul.x, lr.x), min(ul.y, lr.y))
        self.lr = Point(max(ul.x, lr.x), max(ul.y, lr.y))

    def __contains__(self, point):
        """__contains__ (self, point) -> True | False

        Allows syntax: if point in rectangle
        """
        return self.contains(point)

    def __len__(self):
        """__len__ () -> integer

        Returns the number of vertices in this Rectangle.
        """
        return 4

    def __repr__(self):
        return "Rect(ul=%s, lr=%s)" % (str(self.ul), str(self.lr))

    def area(self):
        """area() -> number

        Returns the area of this Rectangle.
        """
        return self.width() * self.height()

    def bounds(self):
        """bounds() -> Rect

        Returns the Rectangle itself.
        """
        return self

    def center(self):
        """center () -> Point

        Returns the center Point of this Rectangle.
        """
        return (self.ul + self.lr) / 2

    def contains(self, point):
        """contains(point) -> True | False

        Returns True if point is contained inside this Rectangle, False otherwise.

        Examples:

        >>> r = Rect( Point(-1, -1), Point(1, 1) )
        >>> r.contains( Point(0, 0) )
        True

        >>> r.contains( Point(2, 3) )
        False
        """
        return (point.x >= self.ul.x and point.x <= self.lr.x) and (
            point.y >= self.ul.y and point.y <= self.lr.y
        )

    def height(self):
        """height () -> number

        Returns the height of this Rectangle.
        """
        return self.lr.y - self.ul.y

    def segments(self):
        """segments () -> [ Line, Line, Line, Line ]

        Return a list of Line segments that comprise this Rectangle.
        """
        ul = self.ul
        lr = self.lr
        ur = Point(lr.x, ul.y)
        ll = Point(ul.x, lr.y)
        return [Line(ul, ur), Line(ur, lr), Line(lr, ll), Line(ll, ul)]

    def width(self):
        """width () -> number

        Returns the width of this Rectangle.
        """
        return self.lr.y - self.ul.x
