#@ boolean (label="boolean") pBoolean
#@ byte (label="byte") pByte
#@ char (label="char") pChar
#@ double (label="double") pDouble
#@ float (label="float") pFloat
#@ int (label="int") pInt
#@ long (label="long") pLong
#@ short (label="short") pShort
#@ Boolean (label="Boolean") oBoolean
#@ Byte (label="Byte") oByte
#@ Character (label="Character") oCharacter
#@ Double (label="Double") oDouble
#@ Float (label="Float") oFloat
#@ Integer (label="Integer") oInteger
#@ Long (label="Long") oLong
#@ Short (label="Short") oShort
#@ int (min=0, max=1000) boundedInteger
#@ double (min=0.2, max=1000.7, stepSize=12.34) boundedDouble
#@ BigInteger bigInteger
#@ BigDecimal bigDecimal
#@ String string
#@ File file
#  Colors aren't supported - see https://github.com/imagej/napari-imagej/issues/62
# #@ ColorRGB color
#@output String result

# A Jython script exercising various parameter types.
# It is the duty of the scripting framework to harvest
# the parameter values from the user, and then display
# the 'result' output parameter, based on its type.

from java.lang import StringBuilder

sb = StringBuilder()

sb.append("Widgets Jython results:\n")

sb.append("\n")
sb.append("\tboolean = " + str(pBoolean) + "\n")
sb.append("\tbyte = " + str(pByte) + "\n")
sb.append("\tchar = " + "'" + str(pChar) + "'\n")
sb.append("\tdouble = " + str(pDouble) + "\n")
sb.append("\tfloat = " + str(pFloat) + "\n")
sb.append("\tint = " + str(pInt) + "\n")
sb.append("\tlong = " + str(pLong) + "\n")
sb.append("\tshort = " + str(pShort) + "\n")

sb.append("\n")
sb.append("\tBoolean = " + str(oBoolean) + "\n")
sb.append("\tByte = " + str(oByte) + "\n")
sb.append("\tCharacter = " + "'" + str(oCharacter) + "'\n")
sb.append("\tDouble = " + str(oDouble) + "\n")
sb.append("\tFloat = " + str(oFloat) + "\n")
sb.append("\tInteger = " + str(oInteger) + "\n")
sb.append("\tLong = " + str(oLong) + "\n")
sb.append("\tShort = " + str(oShort) + "\n")

sb.append("\n")
sb.append("\tbounded integer = " + str(boundedInteger) + "\n")
sb.append("\tbounded double = " + str(boundedDouble) + "\n")

sb.append("\n")
sb.append("\tBigInteger = " + str(bigInteger) + "\n")
sb.append("\tBigDecimal = " + str(bigDecimal) + "\n")
sb.append("\tString = " + str(string) + "\n")
sb.append("\tFile = " + str(file) + "\n")
# Colors aren't supported - see https://github.com/imagej/napari-imagej/issues/62
# sb.append("\tcolor = " + color + "\n")

result = sb.toString()

