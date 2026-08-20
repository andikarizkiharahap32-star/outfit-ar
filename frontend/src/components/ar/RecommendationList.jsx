import React from 'react';

const RecommendationList = ({ recommendations }) => {
  return (
    <div className="mt-8">
      <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
        👕 Hasil Rekomendasi KNN (Akurat)
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {recommendations.map((item) => (
          <div key={item.id} className="border rounded-lg p-2 hover:shadow-md transition">
            <img src={item.image} alt={item.name} className="w-full h-32 object-cover rounded" />
            <p className="text-sm font-semibold mt-2">{item.name}</p>
            <p className="text-xs text-green-600">Match: {item.match_score}%</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RecommendationList;