# Microsoft Fabric notebook cell.
# Prerequisite: attach this notebook to the test Lakehouse and upload fixture.csv to Files/fixture.csv.
from pyspark.sql import functions as F
from pyspark.sql.types import *

schema = StructType([
    StructField('order_id', IntegerType(), False),
    StructField('order_date', DateType(), False),
    StructField('customer_id', StringType(), True),
    StructField('product_id', StringType(), False),
    StructField('region', StringType(), False),
    StructField('warehouse_id', StringType(), False),
    StructField('order_status', StringType(), False),
    StructField('ordered_quantity', IntegerType(), False),
    StructField('fulfilled_quantity', IntegerType(), False),
    StructField('net_sales_amount', DecimalType(18,2), True),
    StructField('cost_of_goods_sold', DecimalType(18,2), True),
    StructField('inventory_value', DecimalType(18,2), True),
])

df = (spark.read
      .option('header', 'true')
      .option('nullValue', '')
      .schema(schema)
      .csv('Files/fixture.csv'))

iso_weekday = F.pmod(F.dayofweek('order_date') + F.lit(5), F.lit(7))
df = (df
    .withColumn('month', F.trunc('order_date', 'month'))
    .withColumn('iso_week', F.weekofyear('order_date'))
    .withColumn('iso_week_year', F.year(F.date_add('order_date', 3 - iso_weekday))))

df.write.format('delta').mode('overwrite').saveAsTable('SaCFact')
print('SaCFact rows:', spark.table('SaCFact').count())
display(spark.table('SaCFact').orderBy('order_id'))
