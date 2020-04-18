
#include "average.h"

Result calculate(int ny, int nx, const float *data, int y0, int x0, int y1,
                 int x1)
 {
	int area=(x1-x0)*(y1-y0);
	double value[3]={0,0,0};
	for (int c=0;c<3;c++)
		{
		for (int x=x0;x<x1;x++)
		       	{
			for (int y=y0;y<y1;y++)
 				{ 
					value[c]=value[c]+data[c+3*x+3*nx*y];
                        	  }
		         }
 		 value[c]=value[c]/area;
	 }
//Result result{{1.0f, 0.0f, 1.0f}};
Result result {{ float(value[0]),float(value[1]),float (value[2])}};
result.avg[0]= value[0];
result.avg[1]=value[1];
result.avg[2]=value[2];
 return result;

}

